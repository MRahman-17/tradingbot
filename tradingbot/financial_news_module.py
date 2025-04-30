#!/usr/bin/env python3
"""
Financial News Module
Collects and analyzes financial news, fear & greed indices, and social media sentiment
to provide market sentiment analysis for trading decisions.
"""
import os
import json
import logging
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import re
from urllib.parse import urlencode
import time
import random
from enhanced_sentiment import EnhancedSentimentAnalyzer
from news_verification import NewsVerifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Financial News")


class FinancialNewsCollector:
    """Collects and analyzes financial news and market sentiment data"""

    def __init__(self):
        """Initialize the news collector"""
        self.config = {
            "api_keys": {
                "alphavantage": os.environ.get("ALPHA_VANTAGE_API_KEY", ""),
                "newsapi": os.environ.get("NEWS_API_KEY", ""),
                "finnhub": os.environ.get("FINNHUB_API_KEY", ""),
                "twitter_bearer": os.environ.get("TWITTER_BEARER_TOKEN", "")
            },
            "endpoints": {
                "fear_greed": "https://api.alternative.me/fng/",
                "alpha_news": "https://www.alphavantage.co/query",
                "news_api": "https://newsapi.org/v2/everything",
                "finnhub_news": "https://finnhub.io/api/v1/news",
                "twitter": "https://api.twitter.com/2/tweets/search/recent"
            },
            "sentiment_weights": {
                "news": 0.5,
                "social": 0.3,
                "fear_greed": 0.2
            },
            "cache_duration": 3600,  # 1 hour cache for API results
            "news_lookback_days": 3,  # Days of news to analyze
            "use_cache": True
        }

        # Initialize cache
        self.cache = {}
        self.cache_timestamps = {}

        # Create necessary directories
        os.makedirs("data/news", exist_ok=True)
        os.makedirs("data/sentiment", exist_ok=True)

        # Track news sentiment by symbol
        self.news_sentiment = {}
        self.fear_greed_data = None
        self.social_sentiment = {}

        logger.info("Financial News Collector initialized")

    def load_config(self, config_path="config/news_config.json"):
        """Load configuration from file"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with default config
                    for key, value in loaded_config.items():
                        if key in self.config and isinstance(self.config[key], dict):
                            self.config[key].update(value)
                        else:
                            self.config[key] = value
                logger.info("News configuration loaded")
            else:
                # Save default config
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, 'w') as f:
                    json.dump(self.config, f, indent=4)
                logger.info("Default news configuration saved")
        except Exception as e:
            logger.error(f"Error loading news configuration: {e}")

    def update_fear_greed_index(self):
        """Update the Fear & Greed Index data"""
        cache_key = "fear_greed"

        # Check cache first if enabled
        if self.config["use_cache"] and cache_key in self.cache:
            cache_age = time.time() - self.cache_timestamps.get(cache_key, 0)
            if cache_age < self.config["cache_duration"]:
                logger.info("Using cached Fear & Greed Index")
                self.fear_greed_data = self.cache[cache_key]
                return self.fear_greed_data

        try:
            url = self.config["endpoints"]["fear_greed"]
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()

                if "data" in data and len(data["data"]) > 0:
                    latest = data["data"][0]

                    # Store in a standardized format
                    self.fear_greed_data = {
                        "timestamp": datetime.now().isoformat(),
                        "score": int(latest["value"]),
                        "classification": latest["value_classification"],
                        "prev_close": int(data["data"][1]["value"]) if len(data["data"]) > 1 else None,
                        "prev_week": int(data["data"][7]["value"]) if len(data["data"]) > 7 else None,
                        "prev_month": int(data["data"][30]["value"]) if len(data["data"]) > 30 else None
                    }

                    # Add market regime classification
                    self.fear_greed_data["market_regime"] = self._classify_market_regime(self.fear_greed_data["score"])

                    # Save to cache
                    self.cache[cache_key] = self.fear_greed_data
                    self.cache_timestamps[cache_key] = time.time()

                    # Save to file
                    with open("data/sentiment/fear_greed_latest.json", 'w') as f:
                        json.dump(self.fear_greed_data, f, indent=4)

                    logger.info(
                        f"Fear & Greed Index updated: {self.fear_greed_data['score']} ({self.fear_greed_data['classification']})")
                    return self.fear_greed_data
                else:
                    logger.warning("No Fear & Greed data returned")
            else:
                logger.error(f"Error fetching Fear & Greed Index: {response.status_code}")

            # If we reach here, try to load from file as fallback
            if os.path.exists("data/sentiment/fear_greed_latest.json"):
                with open("data/sentiment/fear_greed_latest.json", 'r') as f:
                    self.fear_greed_data = json.load(f)
                logger.info("Using saved Fear & Greed Index data")
                return self.fear_greed_data

        except Exception as e:
            logger.error(f"Error updating Fear & Greed Index: {e}")

        # If all else fails, return a default neutral value
        self.fear_greed_data = {
            "timestamp": datetime.now().isoformat(),
            "score": 50,
            "classification": "Neutral",
            "market_regime": "Neutral",
            "prev_close": None,
            "prev_week": None,
            "prev_month": None
        }

        return self.fear_greed_data

    def _classify_market_regime(self, fear_greed_score):
        """Classify the market regime based on fear & greed score"""
        if fear_greed_score >= 80:
            return "Extreme Greed - Potential Top"
        elif fear_greed_score >= 65:
            return "Greed - Bullish"
        elif fear_greed_score >= 45:
            return "Neutral - Range Bound"
        elif fear_greed_score >= 25:
            return "Fear - Bearish"
        else:
            return "Extreme Fear - Potential Bottom"

    def get_company_news(self, symbol, days=None):
        """Get company-specific news from multiple sources with verification"""
        # Original implementation to get news items
        news_items = self._get_original_news_items(symbol, days)

        # Add verification
        if not hasattr(self, 'news_verifier'):
            self.news_verifier = NewsVerifier()

        # Verify each news item
        verified_items = []
        for item in news_items:
            verified_item = self.news_verifier.verify_news_item(item, news_items)
            # Calculate adjusted relevance based on verification and time
            self.news_verifier.calculate_news_relevance(verified_item)
            verified_items.append(verified_item)

        # Sort by adjusted relevance
        verified_items.sort(key=lambda x: x.get('adjusted_relevance', 0), reverse=True)

        return verified_items
        """Get company-specific news from multiple sources"""
        if days is None:
            days = self.config["news_lookback_days"]

        cache_key = f"news_{symbol}_{days}"

        # Check cache first if enabled
        if self.config["use_cache"] and cache_key in self.cache:
            cache_age = time.time() - self.cache_timestamps.get(cache_key, 0)
            if cache_age < self.config["cache_duration"]:
                logger.info(f"Using cached news for {symbol}")
                return self.cache[cache_key]

        # Define date range for news search
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        news_items = []

        # Get news from Alpha Vantage if API key is available
        if self.config["api_keys"]["alphavantage"]:
            try:
                params = {
                    "function": "NEWS_SENTIMENT",
                    "tickers": symbol,
                    "apikey": self.config["api_keys"]["alphavantage"],
                    "limit": 50
                }

                response = requests.get(self.config["endpoints"]["alpha_news"], params=params)

                if response.status_code == 200:
                    data = response.json()
                    if "feed" in data:
                        for item in data["feed"]:
                            # Check if within date range
                            pub_time = datetime.fromisoformat(item["time_published"].replace("Z", "+00:00"))
                            if start_date <= pub_time <= end_date:
                                news_items.append({
                                    "title": item["title"],
                                    "summary": item.get("summary", ""),
                                    "url": item["url"],
                                    "source": item["source"],
                                    "published": item["time_published"],
                                    "sentiment": float(item.get("overall_sentiment_score", 0)),
                                    "relevance": float(
                                        item.get("relevance_score", 0.5) if "relevance_score" in item else 0.5)
                                })
                else:
                    logger.warning(f"Alpha Vantage News API returned status code {response.status_code}")
            except Exception as e:
                logger.error(f"Error fetching Alpha Vantage news for {symbol}: {e}")

        # Get news from News API if API key is available
        if self.config["api_keys"]["newsapi"]:
            try:
                # Format dates for News API
                start_str = start_date.strftime("%Y-%m-%d")
                end_str = end_date.strftime("%Y-%m-%d")

                params = {
                    "q": f"{symbol} OR {self._get_company_name(symbol)}",
                    "from": start_str,
                    "to": end_str,
                    "language": "en",
                    "sortBy": "relevancy",
                    "apiKey": self.config["api_keys"]["newsapi"],
                    "pageSize": 100
                }

                response = requests.get(self.config["endpoints"]["news_api"], params=params)

                if response.status_code == 200:
                    data = response.json()
                    if "articles" in data:
                        for item in data["articles"]:
                            # Only add if we don't already have this URL
                            if not any(news["url"] == item["url"] for news in news_items):
                                # Calculate sentiment using simple keyword analysis since News API doesn't provide sentiment
                                sentiment = self._simple_sentiment_analysis(
                                    item["title"] + " " + (item["description"] or ""))

                                news_items.append({
                                    "title": item["title"],
                                    "summary": item.get("description", ""),
                                    "url": item["url"],
                                    "source": item["source"]["name"],
                                    "published": item["publishedAt"],
                                    "sentiment": sentiment,
                                    "relevance": 0.5  # Default relevance
                                })
                else:
                    logger.warning(f"News API returned status code {response.status_code}")
            except Exception as e:
                logger.error(f"Error fetching News API content for {symbol}: {e}")

        # Get news from Finnhub if API key is available
        if self.config["api_keys"]["finnhub"]:
            try:
                # Convert dates to Unix timestamps for Finnhub
                start_unix = int(start_date.timestamp())
                end_unix = int(end_date.timestamp())

                params = {
                    "symbol": symbol,
                    "from": start_unix,
                    "to": end_unix,
                    "token": self.config["api_keys"]["finnhub"]
                }

                response = requests.get(self.config["endpoints"]["finnhub_news"], params=params)

                if response.status_code == 200:
                    data = response.json()
                    for item in data:
                        # Only add if we don't already have this URL
                        if not any(news["url"] == item["url"] for news in news_items):
                            # Calculate sentiment using simple keyword analysis
                            sentiment = self._simple_sentiment_analysis(
                                item["headline"] + " " + (item.get("summary", "") or ""))

                            news_items.append({
                                "title": item["headline"],
                                "summary": item.get("summary", ""),
                                "url": item["url"],
                                "source": item["source"],
                                "published": datetime.fromtimestamp(item["datetime"]).isoformat(),
                                "sentiment": sentiment,
                                "relevance": 0.7  # Higher default relevance for Finnhub
                            })
                else:
                    logger.warning(f"Finnhub API returned status code {response.status_code}")
            except Exception as e:
                logger.error(f"Error fetching Finnhub news for {symbol}: {e}")

        # Save to cache
        self.cache[cache_key] = news_items
        self.cache_timestamps[cache_key] = time.time()

        # Save to file
        with open(f"data/news/{symbol}_latest.json", 'w') as f:
            json.dump(news_items, f, indent=4)

        logger.info(f"Retrieved {len(news_items)} news items for {symbol}")
        return news_items

    def _get_company_name(self, symbol):
        """Get company name from symbol for better news searches"""
        # Hard-coded mapping for common symbols
        company_map = {
            "AAPL": "Apple",
            "MSFT": "Microsoft",
            "AMZN": "Amazon",
            "GOOGL": "Google OR Alphabet",
            "GOOG": "Google OR Alphabet",
            "META": "Meta OR Facebook",
            "TSLA": "Tesla",
            "NVDA": "NVIDIA",
            "V": "Visa",
            "JPM": "JPMorgan",
            "JNJ": "Johnson & Johnson",
            "WMT": "Walmart",
            "PG": "Procter & Gamble",
            "MA": "Mastercard",
            "UNH": "UnitedHealth",
            "HD": "Home Depot",
            "BAC": "Bank of America",
            "XOM": "Exxon Mobil",
            "AVGO": "Broadcom",
            "KO": "Coca-Cola",
            "PEP": "PepsiCo",
            "ABBV": "AbbVie",
            "COST": "Costco",
            "TMO": "Thermo Fisher",
            "MRK": "Merck"
        }

        return company_map.get(symbol, symbol)

    def _simple_sentiment_analysis(self, text):
        """Legacy function that now uses the enhanced analyzer"""
        if not hasattr(self, 'sentiment_analyzer'):
            self.sentiment_analyzer = EnhancedSentimentAnalyzer()

        return self.sentiment_analyzer.analyze_sentiment(text)
        """Simple rule-based sentiment analysis for news content"""
        text = text.lower()

        # Define sentiment keywords
        positive_words = [
            'gain', 'gains', 'profit', 'profits', 'positive', 'up', 'upside', 'bull', 'bullish',
            'rise', 'rising', 'rose', 'improve', 'improves', 'improved', 'improving', 'improvement',
            'beat', 'beats', 'exceeded', 'exceeds', 'outperform', 'outperforms', 'outperformed',
            'strong', 'stronger', 'strongest', 'strength', 'high', 'higher', 'highest',
            'opportunity', 'opportunities', 'success', 'successful', 'grow', 'growth', 'growing'
        ]

        negative_words = [
            'loss', 'losses', 'negative', 'down', 'downside', 'bear', 'bearish',
            'fall', 'falling', 'fell', 'decline', 'declines', 'declined', 'declining',
            'miss', 'misses', 'missed', 'underperform', 'underperforms', 'underperformed',
            'weak', 'weaker', 'weakest', 'weakness', 'low', 'lower', 'lowest',
            'risk', 'risks', 'risky', 'warning', 'fail', 'failure', 'failing', 'failed',
            'drop', 'drops', 'dropped', 'dropping', 'cut', 'cuts', 'cutting'
        ]

        # Super negative words with higher weight
        very_negative_words = [
            'crash', 'crisis', 'bankruptcy', 'bankrupt', 'collapse', 'disaster', 'catastrophe',
            'plummet', 'plummets', 'plummeted', 'plummeting', 'scandal', 'investigation', 'lawsuit',
            'layoff', 'layoffs', 'recession', 'depression', 'default', 'panic', 'sell-off'
        ]

        # Count word occurrences
        positive_count = sum(1 for word in positive_words if re.search(r'\b' + word + r'\b', text))
        negative_count = sum(1 for word in negative_words if re.search(r'\b' + word + r'\b', text))
        very_negative_count = sum(1 for word in very_negative_words if re.search(r'\b' + word + r'\b', text))

        # Calculate sentiment score (-1 to 1)
        total_count = positive_count + negative_count + (very_negative_count * 2)
        if total_count == 0:
            return 0  # Neutral

        sentiment = (positive_count - negative_count - (very_negative_count * 2)) / float(total_count)

        # Scale from [-1, 1] to [-1, 1]
        return max(min(sentiment, 1), -1)

    def get_social_sentiment(self, symbol):
        """Get social media sentiment for a symbol"""
        cache_key = f"social_{symbol}"

        # Check cache first if enabled
        if self.config["use_cache"] and cache_key in self.cache:
            cache_age = time.time() - self.cache_timestamps.get(cache_key, 0)
            if cache_age < self.config["cache_duration"]:
                logger.info(f"Using cached social sentiment for {symbol}")
                return self.cache[cache_key]

        social_data = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "sentiment_score": 0,
            "volume": 0,
            "twitter_sentiment": None
        }

        # Get Twitter sentiment if bearer token is available
        if self.config["api_keys"]["twitter_bearer"]:
            try:
                # Search for tweets about the symbol and company name
                query = f"${symbol} OR {self._get_company_name(symbol)} lang:en -is:retweet"

                # Twitter v2 API parameters
                params = {
                    "query": query,
                    "max_results": 100,
                    "tweet.fields": "created_at,public_metrics"
                }

                headers = {
                    "Authorization": f"Bearer {self.config['api_keys']['twitter_bearer']}"
                }

                url = f"{self.config['endpoints']['twitter']}?{urlencode(params)}"
                response = requests.get(url, headers=headers)

                if response.status_code == 200:
                    data = response.json()

                    if "data" in data and data["data"]:
                        tweets = data["data"]

                        # Analyze sentiment for each tweet
                        sentiments = []
                        total_engagement = 0

                        for tweet in tweets:
                            tweet_text = tweet.get("text", "")
                            sentiment = self._simple_sentiment_analysis(tweet_text)

                            # Calculate engagement for weighting
                            engagement = sum(tweet.get("public_metrics", {}).get(metric, 0)
                                             for metric in ["like_count", "reply_count", "retweet_count"])

                            # Weight by engagement
                            sentiments.append((sentiment, max(1, engagement)))
                            total_engagement += max(1, engagement)

                        # Calculate weighted average sentiment
                        if sentiments:
                            weighted_sentiment = sum(s[0] * s[1] for s in sentiments) / total_engagement

                            social_data["twitter_sentiment"] = {
                                "score": weighted_sentiment,
                                "volume": len(tweets),
                                "engagement": total_engagement
                            }

                            # Set overall sentiment to Twitter sentiment
                            social_data["sentiment_score"] = weighted_sentiment
                            social_data["volume"] = len(tweets)
                else:
                    logger.warning(f"Twitter API returned status code {response.status_code}")
            except Exception as e:
                logger.error(f"Error fetching Twitter sentiment for {symbol}: {e}")

        # If no data obtained, use a randomly generated mild sentiment
        if social_data["sentiment_score"] == 0:
            # Generate random sentiment between -0.3 and 0.3
            social_data["sentiment_score"] = random.uniform(-0.3, 0.3)
            social_data["volume"] = random.randint(10, 100)
            logger.info(f"Using simulated social sentiment for {symbol}")

        # Save to cache
        self.cache[cache_key] = social_data
        self.cache_timestamps[cache_key] = time.time()

        # Save to social sentiment tracking
        self.social_sentiment[symbol] = social_data

        # Save to file
        with open(f"data/sentiment/social_{symbol}_latest.json", 'w') as f:
            json.dump(social_data, f, indent=4)

        logger.info(f"Social sentiment for {symbol}: {social_data['sentiment_score']:.4f}")
        return social_data

    def update_news_data(self, symbols):
        """Update news data for multiple symbols"""
        # Make sure the fear & greed index is updated
        if not self.fear_greed_data:
            self.update_fear_greed_index()

        # Process each symbol
        for symbol in symbols:
            try:
                # Get news data
                news_items = self.get_company_news(symbol)

                # Get social sentiment
                social_data = self.get_social_sentiment(symbol)

                # Calculate overall news sentiment
                if news_items:
                    # Weight by relevance and recency
                    weighted_sentiments = []
                    total_weight = 0

                    for item in news_items:
                        try:
                            # Calculate recency weight (newer = higher weight)
                            pub_time = datetime.fromisoformat(item["published"].replace("Z", "+00:00"))
                            days_old = (datetime.now() - pub_time).total_seconds() / 86400
                            recency_weight = max(0.2, 1 - (days_old / 7))  # 0.2 to 1.0 based on age

                            # Calculate relevance weight (0.1 to 1.0)
                            relevance_weight = max(0.1, min(1.0, item["relevance"]))

                            # Combine weights
                            weight = recency_weight * relevance_weight

                            weighted_sentiments.append((item["sentiment"], weight))
                            total_weight += weight
                        except Exception as e:
                            logger.warning(f"Error processing news item for {symbol}: {e}")

                    # Calculate weighted average sentiment
                    if weighted_sentiments and total_weight > 0:
                        news_sentiment = sum(s[0] * s[1] for s in weighted_sentiments) / total_weight
                    else:
                        news_sentiment = 0  # Neutral if no valid items
                else:
                    news_sentiment = 0  # Neutral if no news

                # Store sentiment
                self.news_sentiment[symbol] = news_sentiment

                logger.info(f"News sentiment for {symbol}: {news_sentiment:.4f}")
            except Exception as e:
                logger.error(f"Error updating news data for {symbol}: {e}")
                self.news_sentiment[symbol] = 0  # Neutral on error

        return self.news_sentiment

    def get_finance_sentiment_factors(self, symbol):
        """Get all sentiment factors for a symbol"""
        # Ensure we have data
        if symbol not in self.news_sentiment:
            self.update_news_data([symbol])

        if not self.fear_greed_data:
            self.update_fear_greed_index()

        if symbol not in self.social_sentiment:
            self.get_social_sentiment(symbol)

        # Get all sentiment values
        news_sentiment = self.news_sentiment.get(symbol, 0)

        social_sentiment = self.social_sentiment.get(symbol, {}).get("sentiment_score", 0)

        # Convert fear & greed (0-100) to (-1 to 1) scale
        if self.fear_greed_data:
            fear_greed_sentiment = (self.fear_greed_data["score"] - 50) / 50
        else:
            fear_greed_sentiment = 0

        # Get weight configuration
        weights = self.config["sentiment_weights"]

        # Calculate combined sentiment
        combined_sentiment = (
                news_sentiment * weights["news"] +
                social_sentiment * weights["social"] +
                fear_greed_sentiment * weights["fear_greed"]
        )

        # Create sentiment factors result
        sentiment_factors = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "news_sentiment": news_sentiment,
            "social_sentiment": social_sentiment,
            "fear_greed_sentiment": fear_greed_sentiment,
            "fear_greed_score": self.fear_greed_data["score"] if self.fear_greed_data else 50,
            "fear_greed_classification": self.fear_greed_data["classification"] if self.fear_greed_data else "Neutral",
            "market_regime": self.fear_greed_data["market_regime"] if self.fear_greed_data else "Neutral",
            "combined_sentiment": combined_sentiment,
            "sentiment_signal": self._sentiment_to_signal(combined_sentiment)
        }

        # Save to file
        with open(f"data/sentiment/{symbol}_factors.json", 'w') as f:
            json.dump(sentiment_factors, f, indent=4)

        return sentiment_factors

    def _sentiment_to_signal(self, sentiment):
        """Convert sentiment score to trading signal (0 to 1)"""
        # Map from [-1, 1] to [0, 1]
        signal = (sentiment + 1) / 2

        # Add some non-linearity to emphasize extremes
        if sentiment > 0.5:
            # Boost positive sentiment
            signal = 0.5 + (sentiment - 0.5) * 1.2
        elif sentiment < -0.5:
            # Boost negative sentiment
            signal = 0.5 - (abs(sentiment) - 0.5) * 1.2

        # Ensure in range [0, 1]
        return max(0, min(1, signal))

    def get_panic_level(self):
        """Get current market panic level (0-100)"""
        # Update fear & greed if needed
        if not self.fear_greed_data:
            self.update_fear_greed_index()

        if not self.fear_greed_data:
            return 50  # Neutral if no data

        # Invert fear & greed score for panic (100 = extreme fear, 0 = extreme greed)
        panic_score = 100 - self.fear_greed_data["score"]

        # Also check if panic score is much higher than previous periods
        panic_change = 0

        if self.fear_greed_data["prev_close"] is not None:
            panic_change += max(0, self.fear_greed_data["prev_close"] - self.fear_greed_data["score"])

        if self.fear_greed_data["prev_week"] is not None:
            panic_change += max(0, self.fear_greed_data["prev_week"] - self.fear_greed_data["score"]) / 2

        # Adjust panic score based on recent changes (more weight to rapid changes)
        adjusted_panic = panic_score + min(15, panic_change)

        # Cap at 100
        return min(100, adjusted_panic)

    def get_market_risk_factors(self):
        """Get overall market risk factors"""
        # Update fear & greed if needed
        if not self.fear_greed_data:
            self.update_fear_greed_index()

        # Get panic level (0-100)
        panic_level = self.get_panic_level()

        # Calculate risk factors
        risk_factors = {
            "timestamp": datetime.now().isoformat(),
            "panic_level": panic_level,
            "fear_greed_score": self.fear_greed_data["score"] if self.fear_greed_data else 50,
            "fear_greed_classification": self.fear_greed_data["classification"] if self.fear_greed_data else "Neutral",
            "market_regime": self.fear_greed_data["market_regime"] if self.fear_greed_data else "Neutral",
            "risk_level": self._classify_risk_level(panic_level),
            "volatility_expectation": self._classify_volatility_expectation(panic_level)
        }

        # Save to file
        with open("data/sentiment/market_risk_factors.json", 'w') as f:
            json.dump(risk_factors, f, indent=4)

        return risk_factors

    def _classify_risk_level(self, panic_level):
        """Classify risk level based on panic level"""
        if panic_level >= 85:
            return "Extreme Risk - Potential Market Crash"
        elif panic_level >= 70:
            return "High Risk - Significant Downside Potential"
        elif panic_level >= 55:
            return "Elevated Risk - Increased Volatility"
        elif panic_level >= 40:
            return "Moderate Risk - Normal Market Conditions"
        elif panic_level >= 25:
            return "Low Risk - Bullish Environment"
        else:
            return "Very Low Risk - Potential Market Euphoria"

    def _classify_volatility_expectation(self, panic_level):
        """Classify expected volatility based on panic level"""
        if panic_level >= 80 or panic_level <= 20:
            return "Very High - Extreme Market Movements Expected"
        elif panic_level >= 70 or panic_level <= 30:
            return "High - Significant Volatility Expected"
        elif panic_level >= 60 or panic_level <= 35:
            return "Elevated - Above Average Volatility"
        else:
            return "Normal - Average Market Volatility"

    def analyze_event_risks(self, symbols=None):
        """Analyze news for potential high-impact events"""
        # Use provided symbols or all tracked symbols
        if symbols is None:
            symbols = list(self.news_sentiment.keys())
            if not symbols:
                logger.warning("No symbols to analyze for event risks")
                return {}

        # Keywords for high-impact events
        high_impact_patterns = [
            r'announce.*acquisition', r'acquire[ds]', r'merger', r'hostile takeover',
            r'SEC.*investigation', r'investigated by', r'fraud', r'lawsuit', r'legal action',
            r'product recall', r'recall.*product', r'safety concern',
            r'CEO.*resign', r'executive.*depart', r'leadership change',
            r'miss.*earnings', r'earnings.*miss', r'lower.*guidance', r'revise.*downward',
            r'exceed.*earnings', r'earnings.*exceed', r'raise.*guidance', r'revise.*upward',
            r'layoffs', r'cutting.*jobs', r'restructuring', r'downsize',
            r'bankruptcy', r'default', r'debt.*concern', r'liquidity.*issue',
            r'breakthrough', r'new patent', r'FDA approval', r'clinical trial',
            r'dividend.*cut', r'suspend.*dividend', r'dividend.*increase', r'special dividend',
            r'stock split', r'buyback', r'repurchase.*shares', r'dilution', r'secondary offering'
        ]

        event_risks = {}

        for symbol in symbols:
            try:
                # Get recent news
                news_items = self.get_company_news(symbol, days=7)  # Look back a week

                # Analyze for high-impact events
                detected_events = []

                for item in news_items:
                    text = item["title"] + " " + item["summary"]

                    # Check for high-impact patterns
                    for pattern in high_impact_patterns:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        if matches:
                            event_type = self._classify_event_type(pattern)
                            sentiment = item["sentiment"]

                            detected_events.append({
                                "event_type": event_type,
                                "sentiment": sentiment,
                                "title": item["title"],
                                "url": item["url"],
                                "source": item["source"],
                                "published": item["published"]
                            })
                            break  # Only count each news item once

                if detected_events:
                    # Calculate event risk score (higher = more significant events)
                    risk_score = sum(abs(event["sentiment"]) for event in detected_events)

                    event_risks[symbol] = {
                        "events_detected": len(detected_events),
                        "risk_score": float(risk_score),
                        "events": detected_events
                    }

                    logger.info(f"Detected {len(detected_events)} high-impact events for {symbol}")
                else:
                    event_risks[symbol] = {
                        "events_detected": 0,
                        "risk_score": 0,
                        "events": []
                    }
            except Exception as e:
                logger.error(f"Error analyzing event risks for {symbol}: {e}")
                event_risks[symbol] = {
                    "events_detected": 0,
                    "risk_score": 0,
                    "events": [],
                    "error": str(e)
                }

        # Save event risks
        with open("data/sentiment/event_risks.json", 'w') as f:
            json.dump(event_risks, f, indent=4)

        return event_risks

    def _classify_event_type(self, pattern):
        """Classify event type based on matching pattern"""
        pattern = pattern.lower()

        if any(term in pattern for term in ['acquisition', 'acquire', 'merger', 'takeover']):
            return "M&A Activity"
        elif any(term in pattern for term in ['investigation', 'fraud', 'lawsuit', 'legal']):
            return "Legal/Regulatory Issues"
        elif any(term in pattern for term in ['recall', 'safety']):
            return "Product Issues"
        elif any(term in pattern for term in ['ceo', 'executive', 'leadership']):
            return "Management Changes"
        elif any(term in pattern for term in ['earnings', 'guidance']):
            return "Earnings/Guidance"
        elif any(term in pattern for term in ['layoffs', 'jobs', 'restructuring', 'downsize']):
            return "Workforce Changes"
        elif any(term in pattern for term in ['bankruptcy', 'default', 'debt', 'liquidity']):
            return "Financial Health"
        elif any(term in pattern for term in ['breakthrough', 'patent', 'approval', 'trial']):
            return "Product Development"
        elif any(term in pattern for term in ['dividend', 'buyback', 'repurchase', 'split', 'offering']):
            return "Shareholder Returns/Capital Structure"
        else:
            return "Other Significant Event"

    def get_sector_sentiment(self, sector):
        """Get sentiment for an entire sector by analyzing key stocks"""
        # Map sectors to representative stocks
        sector_map = {
            "Technology": ["AAPL", "MSFT", "NVDA", "GOOGL", "META"],
            "Healthcare": ["JNJ", "UNH", "PFE", "ABT", "TMO"],
            "Financials": ["JPM", "BAC", "WFC", "GS", "MS"],
            "Consumer": ["AMZN", "WMT", "HD", "MCD", "NKE"],
            "Energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
            "Communications": ["CMCSA", "VZ", "T", "NFLX", "DIS"],
            "Industrials": ["HON", "UNP", "BA", "CAT", "GE"],
            "Utilities": ["NEE", "DUK", "SO", "D", "AEP"],
            "Materials": ["LIN", "APD", "ECL", "NEM", "FCX"],
            "Real Estate": ["AMT", "PLD", "CCI", "SPG", "EQIX"]
        }

        if sector not in sector_map:
            logger.warning(f"Unknown sector: {sector}")
            return None

        # Get sentiment for each stock in the sector
        sector_stocks = sector_map[sector]
        sentiments = []

        for symbol in sector_stocks:
            try:
                # Update data if needed
                if symbol not in self.news_sentiment:
                    self.update_news_data([symbol])

                # Get sentiment factors
                factors = self.get_finance_sentiment_factors(symbol)
                sentiments.append(factors["combined_sentiment"])
            except Exception as e:
                logger.error(f"Error getting sentiment for {symbol}: {e}")

        # Calculate average sentiment
        if sentiments:
            avg_sentiment = sum(sentiments) / len(sentiments)
        else:
            avg_sentiment = 0

        sector_sentiment = {
            "timestamp": datetime.now().isoformat(),
            "sector": sector,
            "stocks_analyzed": len(sentiments),
            "average_sentiment": float(avg_sentiment),
            "sentiment_signal": self._sentiment_to_signal(avg_sentiment)
        }

        return sector_sentiment

    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()
        self.cache_timestamps.clear()
        logger.info("Cache cleared")
