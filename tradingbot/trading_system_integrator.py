#!/usr/bin/env python3
"""
Trading System Integrator
Connects trading_bot.py and news_trading_integration.py without circular imports
"""
import logging
import importlib

logger = logging.getLogger("Trading System Integrator")


def integrate_components():
    """Integrate all trading system components without circular imports"""
    # Import components when needed, not at the module level
    from news_trading_integration import NewsIntegrator

    # Create news integrator instance
    news_integrator = NewsIntegrator()

    # Dynamically import trading_bot to prevent circular imports
    trading_bot = importlib.import_module('trading_bot')

    # Store original functions for reference (if needed to restore them)
    original_functions = {
        'make_trading_decision': trading_bot.make_trading_decision if hasattr(trading_bot,
                                                                              'make_trading_decision') else None,
        'quantum_prediction': trading_bot.quantum_prediction if hasattr(trading_bot, 'quantum_prediction') else None
    }

    # Define enhanced functions
    def enhanced_make_trading_decision(symbol, quantum_device, config):
        """Enhanced trading decision with news integration"""
        logger.info(f"Making enhanced trading decision for {symbol}")

        # Get historical data
        historical_data = trading_bot.platform_adapter.get_market_data(symbol)

        # Get classical technical signal
        technical_signal = trading_bot.classical_decision(historical_data)

        # Get quantum prediction if available
        quantum_signal = None
        if trading_bot.QUANTUM_AVAILABLE and quantum_device is not None:
            # Get quantum configuration
            quantum_enabled = config.get("quantum_config", {}).get("enabled", True)
            error_threshold = config.get("quantum_config", {}).get("error_threshold", 0.15)

            # Estimate error rate
            error_rate = trading_bot.estimate_quantum_error_rate(quantum_device)

            if quantum_enabled and error_rate <= error_threshold:
                # Get quantum prediction
                quantum_signal, confidence, actual_error = trading_bot.quantum_prediction(
                    symbol, historical_data, quantum_device, error_rate, config
                )

        # Prepare signals for integration
        technical_signals = {symbol: technical_signal}
        quantum_signals = {symbol: quantum_signal if quantum_signal is not None else technical_signal}

        # Get integrated signals
        integrated_signals = news_integrator.get_integrated_signals(
            [symbol], technical_signals, quantum_signals
        )

        # Make trading decision based on integrated signal
        has_position = symbol in trading_bot.trade_history["positions"]
        decision, confidence, reason = news_integrator.make_trading_decision(
            symbol, integrated_signals[symbol],
            trading_bot.trade_history["positions"] if hasattr(trading_bot, 'trade_history') else None
        )

        # Log the decision
        logger.info(f"Trading decision for {symbol}: {decision} (confidence: {confidence:.2f})")
        logger.info(f"Reason: {reason}")

        # Execute trade if needed
        if decision == "BUY" and not has_position:
            logger.info(f"BUY signal for {symbol} based on integrated analysis")
            trading_bot.execute_trade("BUY", symbol)
        elif decision == "SELL" and has_position:
            logger.info(f"SELL signal for {symbol} based on integrated analysis")
            trading_bot.execute_trade("SELL", symbol)
        else:
            logger.info(f"HOLD signal for {symbol}")

        return decision, confidence, reason

    def enhanced_quantum_prediction(symbol, historical_data, quantum_device, error_rate, config):
        """Enhanced quantum prediction with news adjustments"""
        # Get original prediction
        signal, confidence, actual_error = original_functions['quantum_prediction'](
            symbol, historical_data, quantum_device, error_rate, config
        )

        # Get news adjustment factors
        adjustment_factors = news_integrator.get_quantum_adjustment_factors(symbol)

        # Adjust confidence based on news factors
        trend_consistency = adjustment_factors.get("trend_consistency", 1.0)
        adjusted_confidence = confidence * trend_consistency

        # Adjust signal based on sentiment
        sentiment_factor = adjustment_factors.get("sentiment_factor", 1.0)
        sentiment_bias = (sentiment_factor - 1.0) * 0.1  # Scale to small adjustment
        adjusted_signal = max(0, min(1, signal + sentiment_bias))

        return adjusted_signal, adjusted_confidence, actual_error

    # Patch trading_bot with enhanced functions
    if hasattr(trading_bot, 'make_trading_decision'):
        trading_bot.make_trading_decision = enhanced_make_trading_decision
        logger.info("Enhanced trading_bot.make_trading_decision with news integration")

    if hasattr(trading_bot, 'quantum_prediction') and original_functions['quantum_prediction'] is not None:
        trading_bot.quantum_prediction = enhanced_quantum_prediction
        logger.info("Enhanced trading_bot.quantum_prediction with news adjustments")

    # Share platform adapter with news integrator
    if hasattr(trading_bot, 'platform_adapter') and trading_bot.platform_adapter is not None:
        news_integrator.platform_adapter = trading_bot.platform_adapter
        logger.info("Shared platform adapter with news integrator")

    logger.info("Trading system components integrated successfully")
    return news_integrator


# Allow for direct execution
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    integrate_components()
