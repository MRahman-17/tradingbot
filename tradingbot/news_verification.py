import logging
import requests
import json
import os
import math  # Added math module import
from datetime import datetime, timedelta

logger = logging.getLogger("News Verification")


class NewsVerifier:
    def __init__(self):
        self.source_credibility_cache = {}
        self.load_source_database()

    def load_source_database(self):
        """Load or create database of credible sources"""
        db_path = "data/news/source_credibility.json"

        if os.path.exists(db_path):
            try:
                with open(db_path, 'r') as f:
                    self.source_db = json.load(f)
                logger.info("Source credibility database loaded")
            except Exception as e:
                logger.error(f"Error loading source database: {e}")
                self.initialize_default_database(db_path)
        else:
            self.initialize_default_database(db_path)

    def initialize_default_database(self, db_path):
        """Initialize a default source credibility database"""
        self.source_db = {
            "tier_1": {
                "sources": ["Bloomberg", "Reuters", "Financial Times", "Wall Street Journal"],
                "credibility": 1.0
            },
            "tier_2": {
                "sources": ["CNBC", "MarketWatch", "Yahoo Finance", "Barron's", "Forbes"],
                "credibility": 0.8
            },
            "tier_3": {
                "sources": ["Business Insider", "Seeking Alpha", "The Motley Fool", "Investopedia"],
                "credibility": 0.6
            }
        }

        # Save the database
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with open(db_path, 'w') as f:
            json.dump(self.source_db, f, indent=4)

        logger.info("Created default source credibility database")

    def get_source_credibility(self, source_name):
        """Rate the credibility of news sources"""
        # Check cache first
        if source_name in self.source_credibility_cache:
            return self.source_credibility_cache[source_name]

        # Search through tiers
        for tier, info in self.source_db.items():
            if source_name in info["sources"]:
                credibility = info["credibility"]
                # Cache the result
                self.source_credibility_cache[source_name] = credibility
                return credibility

        # Default credibility for unknown sources
        self.source_credibility_cache[source_name] = 0.4
        return 0.4

    def verify_news_item(self, news_item, all_news_items):
        """Verify a news item against other collected items"""
        # Extract key information
        source = news_item.get("source", "Unknown")
        title = news_item.get("title", "")
        published = news_item.get("published", "")

        # Get base credibility from source
        source_credibility = self.get_source_credibility(source)

        # Try to find similar news from other sources
        similar_items = self.find_similar_news(news_item, all_news_items)

        verification_score = source_credibility

        # If we found similar news from other sources, increase verification score
        if similar_items:
            # Average the credibility of all sources reporting this news
            additional_sources_credibility = sum(self.get_source_credibility(item["source"])
                                                 for item in similar_items)

            # Increase verification based on number of corroborating sources
            if len(similar_items) > 0:
                verification_boost = min(0.5, 0.1 * len(similar_items))  # Cap at +0.5
                avg_credibility = additional_sources_credibility / len(similar_items)
                verification_score = min(1.0, source_credibility + verification_boost * avg_credibility)

        # Add verification score to the news item
        news_item["verification_score"] = verification_score

        return news_item

    def find_similar_news(self, target_news, all_news):
        """Find news items similar to the target"""
        similar_items = []

        # Get basic data about target news
        target_title = target_news.get("title", "").lower()
        target_time = datetime.fromisoformat(target_news.get("published", "").replace("Z", "+00:00"))
        target_source = target_news.get("source", "")

        # Set time threshold (24 hours)
        time_threshold = timedelta(hours=24)

        # Find similar news by title overlap and time proximity
        for item in all_news:
            # Skip the same item or same source
            if item == target_news or item.get("source", "") == target_source:
                continue

            # Check time proximity
            item_time = datetime.fromisoformat(item.get("published", "").replace("Z", "+00:00"))
            if abs(target_time - item_time) > time_threshold:
                continue

            # Check title similarity (simple approach - word overlap)
            item_title = item.get("title", "").lower()

            # Count word overlap
            target_words = set(target_title.split())
            item_words = set(item_title.split())
            overlap = len(target_words.intersection(item_words))

            # If significant overlap, consider it similar
            if overlap >= 3 or (overlap / len(target_words) > 0.3):
                similar_items.append(item)

        return similar_items

    def calculate_news_relevance(self, news_item):
        """Calculate relevance of news based on recency and verified status"""
        # Get time since publication
        pub_time = datetime.fromisoformat(news_item.get("published", "").replace("Z", "+00:00"))
        hours_old = (datetime.now() - pub_time).total_seconds() / 3600

        # Apply exponential decay to relevance
        time_factor = math.exp(-0.05 * hours_old)  # Half-life of ~14 hours

        # Factor in verification
        verification_score = news_item.get("verification_score", 0.5)

        # Base relevance score
        base_relevance = news_item.get("relevance", 0.5)

        # Combine factors
        relevance = time_factor * verification_score * base_relevance

        # Update the relevance score
        news_item["adjusted_relevance"] = relevance

        return relevance
