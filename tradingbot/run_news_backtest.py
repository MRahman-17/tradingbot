#!/usr/bin/env python3
"""
Backtest the news sentiment strategy to evaluate its effectiveness
"""
import os
import logging
import json
import argparse
from datetime import datetime, timedelta
from news_backtest import NewsSentimentBacktester

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("News Backtest Runner")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Backtest news sentiment trading strategy')
    parser.add_argument('--symbols', type=str, default="AAPL,MSFT,NVDA",
                        help='Comma-separated list of symbols')
    parser.add_argument('--days', type=int, default=90,
                        help='Number of days to backtest')
    parser.add_argument('--output', type=str, default=None,
                        help='Output file for results (default: auto-generated)')
    return parser.parse_args()


def main():
    """Run the backtest"""
    args = parse_args()

    # Parse symbols
    symbols = [s.strip() for s in args.symbols.split(',')]

    # Set date range
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")

    logger.info(f"Starting backtest for {len(symbols)} symbols from {start_date} to {end_date}")

    # Create backtester
    backtester = NewsSentimentBacktester()

    # Run backtest
    results = backtester.backtest_news_sentiment(symbols, start_date, end_date)

    # Display summary
    if results:
        overall = results["overall"]
        logger.info("====== Backtest Results Summary ======")
        logger.info(f"Symbols tested: {len(symbols)}")
        logger.info(f"Total signals: {overall['total_signals']}")
        logger.info(f"Overall accuracy: {overall.get('accuracy', 0):.4f}")
        logger.info(f"Average return: {overall.get('avg_return', 0):.4%}")
        logger.info(f"Profitable symbols: {overall.get('profitable_symbols', 0)}/{len(symbols)}")
        logger.info("====================================")

        # Show individual symbol results
        logger.info("Symbol Results:")
        for symbol, data in results["symbols"].items():
            if "error" in data:
                logger.info(f"  {symbol}: Error - {data['error']}")
            else:
                logger.info(f"  {symbol}: Accuracy {data.get('accuracy', 0):.4f}, "
                            f"Avg Return {data.get('avg_return', 0):.4%}, "
                            f"Signals: {data.get('signal_count', 0)}")

    # Save custom output if specified
    if args.output:
        try:
            os.makedirs(os.path.dirname(args.output), exist_ok=True)
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=4)
            logger.info(f"Results saved to {args.output}")
        except Exception as e:
            logger.error(f"Error saving results to {args.output}: {e}")


if __name__ == "__main__":
    main()
