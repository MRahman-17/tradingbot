import pandas as pd
import numpy as np
import logging
import json
import os
from datetime import datetime, timedelta
from enhanced_sentiment import EnhancedSentimentAnalyzer

logger = logging.getLogger("News Backtest")


class NewsSentimentBacktester:
    def __init__(self):
        self.sentiment_analyzer = EnhancedSentimentAnalyzer()
        self.results_cache = {}

    def backtest_news_sentiment(self, symbols, start_date, end_date, use_cache=True):
        """Backtest the performance of news sentiment signals"""
        # Generate cache key
        cache_key = f"{'-'.join(symbols)}_{start_date}_{end_date}"

        # Check cache
        if use_cache and cache_key in self.results_cache:
            logger.info("Using cached backtest results")
            return self.results_cache[cache_key]

        # Store results for each symbol
        results = {}
        overall_metrics = {
            "total_signals": 0,
            "correct_signals": 0,
            "avg_return": 0,
            "profitable_symbols": 0
        }

        for symbol in symbols:
            try:
                logger.info(f"Backtesting news sentiment for {symbol}")

                # Get historical price data
                price_data = self.get_historical_prices(symbol, start_date, end_date)

                # Get historical news data
                news_data = self.get_historical_news(symbol, start_date, end_date)

                if news_data and price_data is not None:
                    # Calculate sentiment for each news item
                    for news in news_data:
                        if "sentiment" not in news:
                            news["sentiment"] = self.sentiment_analyzer.analyze_sentiment(
                                news["title"] + " " + news.get("summary", ""))

                    # Group by day and calculate daily sentiment
                    daily_sentiment = self.calculate_daily_sentiment(news_data)

                    # Calculate returns following sentiment signals
                    signals = []
                    for day, sentiment in daily_sentiment.items():
                        if day in price_data.index:
                            # Find price movement after sentiment
                            next_day_return = self.calculate_return_after_sentiment(price_data, day, days=1)
                            five_day_return = self.calculate_return_after_sentiment(price_data, day, days=5)

                            correct_direction = False
                            if sentiment > 0.1 and next_day_return > 0:  # Positive sentiment threshold
                                correct_direction = True
                            elif sentiment < -0.1 and next_day_return < 0:  # Negative sentiment threshold
                                correct_direction = True

                            signals.append({
                                "date": day.strftime("%Y-%m-%d"),
                                "sentiment": float(sentiment),
                                "next_day_return": float(next_day_return),
                                "five_day_return": float(five_day_return),
                                "correct_direction": correct_direction
                            })

                    # Calculate metrics
                    if signals:
                        accuracy = sum(1 for s in signals if s["correct_direction"]) / len(signals)
                        avg_return = sum(s["next_day_return"] for s in signals) / len(signals)
                        avg_5day_return = sum(s["five_day_return"] for s in signals) / len(signals)

                        results[symbol] = {
                            "accuracy": float(accuracy),
                            "avg_return": float(avg_return),
                            "avg_5day_return": float(avg_5day_return),
                            "signal_count": len(signals),
                            "signals": signals
                        }

                        # Update overall metrics
                        overall_metrics["total_signals"] += len(signals)
                        overall_metrics["correct_signals"] += sum(1 for s in signals if s["correct_direction"])
                        overall_metrics["avg_return"] += avg_return
                        if accuracy > 0.5:
                            overall_metrics["profitable_symbols"] += 1
                    else:
                        logger.warning(f"No valid signals found for {symbol}")
                        results[symbol] = {
                            "accuracy": 0,
                            "avg_return": 0,
                            "avg_5day_return": 0,
                            "signal_count": 0,
                            "signals": []
                        }
                else:
                    logger.warning(f"No data available for {symbol}")
                    results[symbol] = {
                        "accuracy": 0,
                        "avg_return": 0,
                        "avg_5day_return": 0,
                        "signal_count": 0,
                        "signals": []
                    }
            except Exception as e:
                logger.error(f"Error backtesting {symbol}: {e}")
                results[symbol] = {
                    "error": str(e),
                    "accuracy": 0,
                    "avg_return": 0,
                    "avg_5day_return": 0,
                    "signal_count": 0,
                    "signals": []
                }

        # Calculate overall metrics
        if overall_metrics["total_signals"] > 0:
            overall_metrics["accuracy"] = overall_metrics["correct_signals"] / overall_metrics["total_signals"]
            overall_metrics["avg_return"] = overall_metrics["avg_return"] / len(symbols)
            overall_metrics["symbol_profitability"] = overall_metrics["profitable_symbols"] / len(symbols)
        else:
            overall_metrics["accuracy"] = 0
            overall_metrics["avg_return"] = 0
            overall_metrics["symbol_profitability"] = 0

        # Compile final results
        final_results = {
            "symbols": results,
            "overall": overall_metrics,
            "backtest_period": {"start": start_date, "end": end_date},
            "timestamp": datetime.now().isoformat()
        }

        # Cache results
        self.results_cache[cache_key] = final_results

        # Save results to file
        self.save_backtest_results(final_results)

        return final_results

    def get_historical_prices(self, symbol, start_date, end_date):
        """Get historical price data for a symbol"""
        # Implement connection to your existing price data source
        # This could connect to your platform_adapter.get_market_data function
        # or load from saved CSV/database
        try:
            # Placeholder - replace with actual implementation
            # Example:
            # return platform_adapter.get_market_data(symbol, start_date, end_date)
            pass
        except Exception as e:
            logger.error(f"Error getting price data for {symbol}: {e}")
            return None

    def get_historical_news(self, symbol, start_date, end_date):
        """Get historical news data for a symbol"""
        # Try to load from your news archive
        news_path = f"data/news/{symbol}_archive.json"

        if os.path.exists(news_path):
            try:
                with open(news_path, 'r') as f:
                    all_news = json.load(f)

                # Filter by date range
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")

                filtered_news = []
                for news in all_news:
                    try:
                        pub_date = datetime.fromisoformat(news["published"].replace("Z", "+00:00"))
                        if start <= pub_date <= end:
                            filtered_news.append(news)
                    except:
                        continue

                return filtered_news
            except Exception as e:
                logger.error(f"Error loading historical news for {symbol}: {e}")
                return []
        else:
            logger.warning(f"No historical news archive found for {symbol}")
            return []

    def calculate_daily_sentiment(self, news_data):
        """Group news by day and calculate sentiment"""
        daily_sentiment = {}

        for news in news_data:
            try:
                pub_date = datetime.fromisoformat(news["published"].replace("Z", "+00:00"))
                day = pub_date.date()

                if day not in daily_sentiment:
                    daily_sentiment[day] = []

                # Add weight based on source credibility
                weight = news.get("verification_score", 0.5) * news.get("relevance", 1.0)

                daily_sentiment[day].append((news["sentiment"], weight))
            except:
                continue

        # Calculate weighted average sentiment for each day
        for day in daily_sentiment:
            if daily_sentiment[day]:
                total_weight = sum(weight for _, weight in daily_sentiment[day])
                if total_weight > 0:
                    daily_sentiment[day] = sum(
                        sentiment * weight for sentiment, weight in daily_sentiment[day]) / total_weight
                else:
                    daily_sentiment[day] = 0
            else:
                daily_sentiment[day] = 0

        return daily_sentiment

    def calculate_return_after_sentiment(self, price_data, day, days=1):
        """Calculate return after a sentiment signal"""
        try:
            # Find the index of the day in the price data
            if day in price_data.index:
                day_idx = price_data.index.get_loc(day)

                # Get the closing price on the signal day
                signal_price = price_data['Close'].iloc[day_idx]

                # Get the closing price N days later
                if day_idx + days < len(price_data):
                    future_price = price_data['Close'].iloc[day_idx + days]
                    return (future_price / signal_price) - 1
                else:
                    return 0  # Not enough data for future
            else:
                return 0  # Day not found
        except Exception as e:
            logger.error(f"Error calculating returns: {e}")
            return 0

    def save_backtest_results(self, results):
        """Save backtest results to file"""
        try:
            os.makedirs("data/backtest_results", exist_ok=True)

            # Create filename with timestamp
            filename = f"news_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            file_path = os.path.join("data/backtest_results", filename)

            with open(file_path, 'w') as f:
                json.dump(results, f, indent=4)

            logger.info(f"Backtest results saved to {file_path}")
        except Exception as e:
            logger.error(f"Error saving backtest results: {e}")
