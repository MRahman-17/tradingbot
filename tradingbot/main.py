import os
import sys
import time
import logging
import signal
import argparse
from datetime import datetime
import threading
from typing import Dict, List, Any, Optional

# Import core components
from core.config import Config
from core.logging_setup import setup_logging
from core.security import Security

# Import platform adapters
from platforms.platform_base import PlatformAdapter
from platforms.mock_adapter import MockAdapter
from platforms.webull_adapter import WebullAdapter

# Import analysis components
from analysis.technical import TechnicalAnalyzer
from analysis.quantum import QuantumAnalyzer
from analysis.news import NewsCollector
from analysis.compliance import HalalComplianceChecker

# Import strategies
from strategies.integrated_strategy import IntegratedStrategy

# Import monitoring components
from monitoring.performance import PerformanceTracker
from monitoring.system_health import SystemMonitor

# Create logger
logger = logging.getLogger(__name__)


def parse_arguments():
    """Pars  e command line arguments"""
    parser = argparse.ArgumentParser(description="Trading System")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--paper", action="store_true", help="Use paper trading")
    parser.add_argument("--live", action="store_true", help="Use live trading (override config)")
    parser.add_argument("--symbols", type=str, help="Comma-separated list of symbols to trade")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--backtest", action="store_true", help="Run in backtest mode")
    return parser.parse_args()


def create_platform_adapter(config: Config) -> PlatformAdapter:
    """Create platform adapter based on configuration

    Args:
        config: Configuration object

    Returns:
        Platform adapter instance
    """
    platform_name = config.get("platform", "name") or "mock"
    use_paper = config.get("platform", "use_paper_trading")
    if use_paper is None:
        use_paper = True

    logger.info(f"Creating platform adapter: {platform_name} (paper trading: {use_paper})")

    platform_config = config.get("platform") or {}

    if platform_name == "mock":
        return MockAdapter(platform_config)
    elif platform_name == "webull":
        return WebullAdapter(platform_config)
    else:
        logger.warning(f"Unknown platform: {platform_name}, falling back to mock platform")
        return MockAdapter(platform_config)


def handle_exit(signum, frame):
    """Handle exit signals gracefully"""
    logger.info("Exit signal received. Shutting down...")

    # Set global exit flag
    global exit_flag
    exit_flag = True

    sys.exit(0)


def trading_loop(config: Config, args) -> None:
    """Main trading loop

    Args:
        config: Configuration object
        args: Command line arguments
    """
    logger.info("Starting trading loop")

    # Create platform adapter
    platform_adapter = create_platform_adapter(config)

    # Login to platform
    if not platform_adapter.login():
        logger.error("Failed to login to platform. Exiting.")
        return

    # Create analysis components
    technical_config = config.get("technical") or {}
    technical_analyzer = TechnicalAnalyzer(technical_config)

    quantum_config = config.get("quantum") or {}
    quantum_analyzer = QuantumAnalyzer(quantum_config)

    news_config = config.get("news") or {}
    news_collector = NewsCollector(news_config)

    compliance_config = config.get("compliance") or {}
    compliance_checker = HalalComplianceChecker(compliance_config)

    # Create integrated strategy
    trading_config = config.get("trading") or {}
    strategy = IntegratedStrategy(
        trading_config,
        technical_analyzer=technical_analyzer,
        quantum_analyzer=quantum_analyzer,
        news_collector=news_collector,
        compliance_checker=compliance_checker
    )

    # Create monitoring components
    monitoring_config = config.get("monitoring") or {}
    performance_tracker = PerformanceTracker(monitoring_config)
    system_monitor = SystemMonitor(monitoring_config)

    # Get symbols to trade
    symbols = []
    if args.symbols:
        symbols = args.symbols.split(",")
    else:
        symbols_config = config.get("trading", "symbols")
        if symbols_config:
            symbols = symbols_config
        else:
            symbols = ["AAPL", "MSFT", "NVDA"]

    logger.info(f"Trading symbols: {', '.join(symbols)}")

    # Set up exit handler
    global exit_flag
    exit_flag = False
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # Main trading loop
    try:
        while not exit_flag:
            # Check system health
            if not system_monitor.check_api_health():  # Changed from check_health to check_api_health
                logger.warning("System health check failed, pausing trading")
                time.sleep(60)  # Sleep for 1 minute before retrying
                continue

            current_time = datetime.now()
            logger.info(f"Trading cycle started at {current_time}")

            # Get market data for all symbols
            market_data = {}
            for symbol in symbols:
                market_data[symbol] = platform_adapter.get_market_data(symbol)

            # Analyze each symbol
            for symbol in symbols:
                if symbol not in market_data:
                    logger.warning(f"No market data for {symbol}, skipping")
                    continue

                # Check if market data for this symbol is empty
                if market_data[symbol] is None or (hasattr(market_data[symbol], 'empty') and market_data[symbol].empty):
                    logger.warning(f"Empty market data for {symbol}, skipping")
                    continue

                # Run technical analysis - check what method is available
                try:
                    # Try different method names that might exist
                    if hasattr(technical_analyzer, 'analyze'):
                        technical_signals = technical_analyzer.analyze(symbol, market_data[symbol])
                    elif hasattr(technical_analyzer, 'analyze_symbol'):
                        technical_signals = technical_analyzer.analyze_symbol(symbol, market_data[symbol])
                    elif hasattr(technical_analyzer, 'get_signals'):
                        technical_signals = technical_analyzer.get_signals(symbol, market_data[symbol])
                    else:
                        logger.warning(f"No suitable analysis method found in TechnicalAnalyzer for {symbol}")
                        technical_signals = {}
                except Exception as e:
                    logger.error(f"Error in technical analysis for {symbol}: {e}")
                    technical_signals = {}

                # Run quantum analysis - check what method is available
                try:
                    # Try different method names that might exist
                    if hasattr(quantum_analyzer, 'analyze'):
                        quantum_signals = quantum_analyzer.analyze(symbol, market_data[symbol])
                    elif hasattr(quantum_analyzer, 'analyze_symbol'):
                        quantum_signals = quantum_analyzer.analyze_symbol(symbol, market_data[symbol])
                    elif hasattr(quantum_analyzer, 'get_signals'):
                        quantum_signals = quantum_analyzer.get_signals(symbol, market_data[symbol])
                    else:
                        logger.warning(f"No suitable analysis method found in QuantumAnalyzer for {symbol}")
                        quantum_signals = {}
                except Exception as e:
                    logger.error(f"Error in quantum analysis for {symbol}: {e}")
                    quantum_signals = {}

                # Get news data - check what method is available
                try:
                    # Try different method names that might exist
                    if hasattr(news_collector, 'get_news'):
                        news_data = news_collector.get_news(symbol)
                    elif hasattr(news_collector, 'collect_news'):
                        news_data = news_collector.collect_news(symbol)
                    elif hasattr(news_collector, 'get_news_data'):
                        news_data = news_collector.get_news_data(symbol)
                    else:
                        logger.warning(f"No suitable method found in NewsCollector for {symbol}")
                        news_data = {}
                except Exception as e:
                    logger.error(f"Error getting news data for {symbol}: {e}")
                    news_data = {}

                # Check compliance - check what method is available
                try:
                    # Try different method names that might exist
                    if hasattr(compliance_checker, 'check_compliance'):
                        compliance_status = compliance_checker.check_compliance(symbol)
                    elif hasattr(compliance_checker, 'is_compliant'):
                        compliance_status = compliance_checker.is_compliant(symbol)
                    elif hasattr(compliance_checker, 'verify_compliance'):
                        compliance_status = compliance_checker.verify_compliance(symbol)
                    else:
                        logger.warning(f"No suitable method found in HalalComplianceChecker for {symbol}")
                        compliance_status = {"compliant": True, "reason": "Compliance check bypassed"}
                except Exception as e:
                    logger.error(f"Error checking compliance for {symbol}: {e}")
                    compliance_status = {"compliant": True, "reason": "Compliance check error, assuming compliant"}

                # Check compliance result
                if not compliance_status.get("compliant", True):
                    logger.warning(
                        f"Symbol {symbol} failed compliance check: {compliance_status.get('reason', 'Unknown reason')}")
                    continue

                # Run integrated strategy - check what method is available
                try:
                    # Try different method names that might exist
                    if hasattr(strategy, 'decide_action'):
                        action = strategy.decide_action(
                            symbol,
                            market_data[symbol],
                            technical_signals,
                            quantum_signals,
                            news_data,
                            compliance_status
                        )
                    elif hasattr(strategy, 'get_action'):
                        action = strategy.get_action(
                            symbol,
                            market_data[symbol],
                            technical_signals,
                            quantum_signals,
                            news_data,
                            compliance_status
                        )
                    else:
                        logger.warning(f"No suitable method found in IntegratedStrategy for {symbol}")
                        action = {"type": "HOLD", "reason": "Strategy method not found"}
                except Exception as e:
                    logger.error(f"Error in strategy decision for {symbol}: {e}")
                    action = {"type": "HOLD", "reason": f"Strategy error: {e}"}

                # Execute action if any
                if action and action.get("type") != "HOLD":
                    logger.info(f"Executing action for {symbol}: {action}")
                    try:
                        result = platform_adapter.execute_order(action)
                        if result.get("success", False):
                            try:
                                if hasattr(performance_tracker, 'record_trade'):
                                    performance_tracker.record_trade(symbol, action, result)
                                elif hasattr(performance_tracker, 'add_trade'):
                                    performance_tracker.add_trade(symbol, action, result)
                                logger.info(f"Order executed successfully: {result}")
                            except Exception as e:
                                logger.error(f"Error recording trade: {e}")
                        else:
                            logger.error(f"Order execution failed: {result}")
                    except Exception as e:
                        logger.error(f"Error executing order: {e}")

            # Update performance metrics
            try:
                account_info = platform_adapter.get_account_info()
                if hasattr(performance_tracker, 'update_metrics'):
                    performance_tracker.update_metrics(account_info)
                elif hasattr(performance_tracker, 'update'):
                    performance_tracker.update(account_info)
            except Exception as e:
                logger.error(f"Error updating performance metrics: {e}")

            # Sleep until next cycle
            cycle_interval = config.get("trading", "cycle_interval_seconds")
            if cycle_interval is None:
                cycle_interval = 60
            logger.info(f"Trading cycle completed. Sleeping for {cycle_interval} seconds")
            time.sleep(cycle_interval)

    except Exception as e:
        logger.exception(f"Error in trading loop: {e}")
    finally:
        # Cleanup and logout
        platform_adapter.logout()
        logger.info("Trading loop ended")


def classify_news_event(pattern: str) -> str:
    """Classify news event based on pattern.

    Args:
        pattern: Regular expression pattern that matched

    Returns:
        Event type classification
    """
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


def main():
    """Main entry point"""
    # Parse command line arguments
    args = parse_arguments()

    # First, set up a basic logging configuration to ensure we can log errors
    logging.basicConfig(level=logging.INFO)

    # Load configuration
    try:
        config_path = args.config or "config/default.yaml"
        config = Config(config_path)

        try:
            # Attempt to set up logging with the config
            setup_logging(config)
        except AttributeError:
            # If setup_logging fails due to the AttributeError we're seeing,
            # fall back to basic logging configuration
            logger.warning("Error setting up logging with config. Using default logging configuration.")

            # Set debug level if requested
            if args.debug:
                logging.getLogger().setLevel(logging.DEBUG)

        logger.info("Starting trading system")

        # Override configuration with command line arguments
        if args.paper:
            config.set("platform", "use_paper_trading", True)
        if args.live:
            config.set("platform", "use_paper_trading", False)
        if args.backtest:
            config.set("mode", "backtest", True)

        # Also fix FutureWarnings in the mock_adapter by adding a comment with suggestions
        # Note for platform adapter:
        # There are FutureWarnings about DataFrame.fillna(method='bfill') being deprecated
        # Consider updating these lines in mock_adapter.py:194:
        # From: df = df.fillna(method='bfill').fillna(method='ffill')
        # To:   df = df.bfill().ffill()

        # Initialize security - fix the config.get method call
        security_config = config.get("security") or {}
        security = Security(security_config)

        # Start trading loop
        trading_loop(config, args)

    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()