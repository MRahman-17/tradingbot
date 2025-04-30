#!/usr/bin/env python3
"""
Enhanced test script for the Financial News Module
Tests various functionality including fear & greed index, news sentiment,
and integration with trading decision-making
"""
import os
import sys
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("News Module Test")

# Import the FinancialNewsCollector
from financial_news_module import FinancialNewsCollector


def main():
    """Main test function"""
    logger.info("=== FINANCIAL NEWS MODULE TEST ===")

    # Create news collector
    news_collector = FinancialNewsCollector()

    # Load configuration
    news_collector.load_config()

    # Test symbols
    symbols = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"]

    # Test fear & greed index update
    logger.info("\nTesting Fear & Greed Index:")
    fear_greed_data = news_collector.update_fear_greed_index()
    print(f"Fear & Greed Index: {fear_greed_data['score']} ({fear_greed_data['classification']})")
    print(f"Market Regime: {fear_greed_data['market_regime']}")

    # Get panic level
    panic_level = news_collector.get_panic_level()
    print(f"Market Panic Level: {panic_level}/100")

    # Get market risk factors
    logger.info("\nTesting Market Risk Factors:")
    risk_factors = news_collector.get_market_risk_factors()
    print(f"Risk Level: {risk_factors['risk_level']}")
    print(f"Volatility Expectation: {risk_factors['volatility_expectation']}")

    # Update news data for all symbols
    logger.info("\nUpdating News Data:")
    news_sentiment = news_collector.update_news_data(symbols)
    for symbol, sentiment in news_sentiment.items():
        print(f"{symbol} News Sentiment: {sentiment:.4f}")

    # Test social sentiment
    logger.info("\nTesting Social Sentiment:")
    for symbol in symbols[:2]:  # Just test a couple to save time
        social_data = news_collector.get_social_sentiment(symbol)
        print(f"{symbol} Social Sentiment: {social_data['sentiment_score']:.4f}")

    # Test getting sentiment factors
    logger.info("\nTesting Sentiment Factors:")
    for symbol in symbols:
        factors = news_collector.get_finance_sentiment_factors(symbol)
        print(f"\n{symbol} Sentiment Factors:")
        print(f"  News Sentiment: {factors['news_sentiment']:.4f}")
        print(f"  Social Sentiment: {factors['social_sentiment']:.4f}")
        print(f"  Fear & Greed Sentiment: {factors['fear_greed_sentiment']:.4f}")
        print(f"  Combined Sentiment: {factors['combined_sentiment']:.4f}")
        print(f"  Sentiment Signal (0-1): {factors['sentiment_signal']:.4f}")

    # Test event risk analysis
    logger.info("\nTesting Event Risk Analysis:")
    event_risks = news_collector.analyze_event_risks(symbols)
    for symbol, risk_data in event_risks.items():
        print(f"{symbol} Event Risk Score: {risk_data['risk_score']:.2f} ({risk_data['events_detected']} events)")

        # Print details of the first event if any
        if risk_data['events']:
            event = risk_data['events'][0]
            print(f"  Example Event: {event['event_type']} - {event['title']}")

    # Test sector sentiment
    logger.info("\nTesting Sector Sentiment:")
    sectors = ["Technology", "Healthcare", "Financials"]
    for sector in sectors:
        sector_sentiment = news_collector.get_sector_sentiment(sector)
        if sector_sentiment:
            print(f"{sector} Sector Sentiment: {sector_sentiment['average_sentiment']:.4f}")

    # Save all data to see output files
    logger.info("\nAll test data has been saved to the data directory")

    # Demo integration with trading decision
    logger.info("\nDemo Integration with Trading Decision:")
    for symbol in symbols:
        sentiment_signal = news_collector.get_finance_sentiment_factors(symbol)["sentiment_signal"]
        market_risk = risk_factors["risk_level"]

        # Simple trading decision logic
        if sentiment_signal > 0.7 and "High Risk" not in market_risk:
            decision = "BUY"
        elif sentiment_signal < 0.3 or "Extreme Risk" in market_risk:
            decision = "SELL"
        else:
            decision = "HOLD"

        print(f"{symbol}: Sentiment Signal {sentiment_signal:.2f}, Market Risk '{market_risk}' → {decision}")


if __name__ == "__main__":
    main()
