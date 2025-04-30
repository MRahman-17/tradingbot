#!/usr/bin/env python3
"""
News Trading Integration Module
Integrates financial news analysis with trading bot and quantum components
"""
import os
import sys
import logging
import json
import numpy as np
from datetime import datetime
from adaptive_weights import WeightManager
from resilient_analysis import ResilientNewsAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("News Trading Integration")

# Import the FinancialNewsCollector
from financial_news_module import FinancialNewsCollector


class NewsIntegrator:
    """Integrates news analysis with trading decisions"""

    def __init__(self):
        """Initialize the news integrator"""
        self.news_collector = FinancialNewsCollector()
        self.news_collector.load_config()

        # Create required directories
        os.makedirs("data/integrated_signals", exist_ok=True)

        # Default weights for integration
        self.integration_weights = {
            "technical": 0.4,  # Technical analysis weight
            "quantum": 0.25,  # Quantum analysis weight
            "news": 0.25,  # News sentiment weight
            "market_risk": 0.1  # Market risk factors weight
        }

        # Load custom weights if available
        self._load_weights()

        logger.info("News integrator initialized")

    def _load_weights(self):
        """Load integration weights from file if available"""
        weights_path = "config/integration_weights.json"
        if os.path.exists(weights_path):
            try:
                with open(weights_path, 'r') as f:
                    weights = json.load(f)
                self.integration_weights = weights
                logger.info("Integration weights loaded from file")
            except Exception as e:
                logger.error(f"Error loading integration weights: {e}")

    def update_sentiment_data(self, symbols):
        """Update sentiment data for all symbols"""
        # Update fear & greed index
        self.news_collector.update_fear_greed_index()

        # Update news data
        self.news_collector.update_news_data(symbols)

        # Get market risk factors
        risk_factors = self.news_collector.get_market_risk_factors()

        # Analyze event risks
        event_risks = self.news_collector.analyze_event_risks(symbols)

        logger.info(f"Updated sentiment data for {len(symbols)} symbols")
        return {
            "risk_factors": risk_factors,
            "event_risks": event_risks
        }

    def get_integrated_signals(self, symbols, technical_signals, quantum_signals):
        """
        Integrate news sentiment with technical and quantum signals using adaptive weights

        Args:
            symbols (list): List of stock symbols
            technical_signals (dict): Technical analysis signals (0-1 scale)
            quantum_signals (dict): Quantum analysis signals (0-1 scale)

        Returns:
            dict: Integrated trading signals
        """
        integrated_signals = {}

        # Initialize weight manager if not already done
        if not hasattr(self, 'weight_manager'):
            self.weight_manager = WeightManager()

        # Initialize resilient analyzer
        if not hasattr(self, 'resilient_analyzer'):
            self.resilient_analyzer = ResilientNewsAnalyzer(news_collector=self.news_collector)

        # Make sure we have the latest sentiment data
        self.update_sentiment_data(symbols)

        # Get market risk factors
        risk_factors = self.news_collector.get_market_risk_factors()
        panic_level = risk_factors["panic_level"]

        for symbol in symbols:
            try:
                # Get news sentiment factors with fallback mechanisms
                sentiment_factors = self.resilient_analyzer.get_sentiment_with_fallback(symbol)
                news_signal = sentiment_factors["sentiment_signal"]

                # Get event risks
                event_risks = self.news_collector.analyze_event_risks([symbol])[symbol]

                # Scale risk score to a 0-1 signal (higher risk = lower signal)
                risk_signal = max(0, min(1, 1 - (event_risks["risk_score"] / 5)))

                # Get technical and quantum signals
                technical_signal = technical_signals.get(symbol, 0.5)
                quantum_signal = quantum_signals.get(symbol, 0.5)

                # Get market data for the symbol (for regime detection)
                market_data = None
                if hasattr(self, 'platform_adapter') and self.platform_adapter:
                    market_data = self.platform_adapter.get_market_data(symbol)

                # Calculate confidences for each signal type
                confidences = {
                    "technical": 0.8,  # Technical analysis is generally reliable
                    "quantum": 0.6,  # Quantum is less tested
                    "news": sentiment_factors.get("verification_score", 0.7),  # Based on news verification
                    "market_risk": 0.9  # Market risk factors are reliable indicators
                }

                # Get historical performance if available
                historical_performance = self.get_historical_performance(symbol)

                # Calculate integrated signal with dynamic weights
                integrated_signal, weights = self.weight_manager.get_integrated_signal(
                    symbol,
                    {
                        "technical": technical_signal,
                        "quantum": quantum_signal,
                        "news": news_signal,
                        "market_risk": risk_signal
                    },
                    confidences,
                    market_data,
                    historical_performance
                )

                # Record the integrated signal and components
                integrated_signals[symbol] = {
                    "timestamp": datetime.now().isoformat(),
                    "symbol": symbol,
                    "integrated_signal": float(integrated_signal),
                    "components": {
                        "technical_signal": float(technical_signal),
                        "quantum_signal": float(quantum_signal),
                        "news_signal": float(news_signal),
                        "risk_signal": float(risk_signal)
                    },
                    "weights": weights,
                    "confidences": confidences,
                    "market_risk_level": risk_factors["risk_level"],
                    "panic_level": float(panic_level),
                    "event_risks": event_risks["events_detected"]
                }

                logger.info(f"Integrated signal for {symbol}: {integrated_signal:.4f}")
            except Exception as e:
                logger.error(f"Error calculating integrated signal for {symbol}: {e}")
                # Provide a neutral signal on error
                integrated_signals[symbol] = {
                    "timestamp": datetime.now().isoformat(),
                    "symbol": symbol,
                    "integrated_signal": 0.5,
                    "error": str(e)
                }

        # Save integrated signals
        with open(f"data/integrated_signals/signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
            json.dump(integrated_signals, f, indent=4)

        return integrated_signals

    def get_historical_performance(self, symbol):
        """Get historical performance metrics for different signal types"""
        try:
            # Check if performance data exists
            performance_path = f"data/performance/signal_performance_{symbol}.json"
            if os.path.exists(performance_path):
                with open(performance_path, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Error getting historical performance: {e}")
            return None

    def _adjust_weights_for_market_conditions(self, panic_level):
        """Adjust integration weights based on market conditions"""
        # Copy base weights
        adjusted = self.integration_weights.copy()

        if panic_level >= 75:
            # In high panic, increase weight of news and market risk
            adjusted["news"] += 0.1
            adjusted["market_risk"] += 0.1
            adjusted["technical"] -= 0.15
            adjusted["quantum"] -= 0.05
        elif panic_level <= 25:
            # In low panic/high greed, increase weight of quantum
            adjusted["quantum"] += 0.1
            adjusted["news"] -= 0.05
            adjusted["market_risk"] -= 0.05

        # Normalize weights to sum to 1
        total = sum(adjusted.values())
        for key in adjusted:
            adjusted[key] /= total

        return adjusted

    def make_trading_decision(self, symbol, integrated_signal, positions=None):
        """
        Make a trading decision based on integrated signal

        Args:
            symbol (str): Stock symbol
            integrated_signal (dict): Integrated signal data
            positions (dict): Current positions (optional)

        Returns:
            tuple: (decision, confidence, reason)
        """
        # Check if we have an error
        if "error" in integrated_signal:
            return "HOLD", 0.5, f"Error in signal integration: {integrated_signal['error']}"

        # Extract the signal and components
        signal = integrated_signal["integrated_signal"]
        components = integrated_signal.get("components", {})

        # Check if we have a position
        has_position = False
        if positions and symbol in positions:
            has_position = True

        # Define thresholds
        buy_threshold = 0.7
        sell_threshold = 0.3

        # Additional factors
        market_risk = integrated_signal.get("market_risk_level", "Unknown")
        panic_level = integrated_signal.get("panic_level", 50)
        event_risks = integrated_signal.get("event_risks", 0)

        # Calculate decision confidence
        confidence = abs((signal - 0.5) * 2)  # 0 to 1 scale

        # Special cases first
        if "Extreme Risk" in market_risk and has_position:
            return "SELL", max(0.7, confidence), "Extreme market risk detected"

        if event_risks >= 3 and has_position:
            return "SELL", max(0.6, confidence), f"Multiple high-impact events detected ({event_risks})"

        # Normal signal-based decisions
        if signal > buy_threshold and not has_position:
            reason = f"Strong buy signal ({signal:.2f})"

            # Add component strengths to reason
            component_info = []
            if components.get("technical_signal", 0) > 0.7:
                component_info.append("technical")
            if components.get("quantum_signal", 0) > 0.7:
                component_info.append("quantum")
            if components.get("news_signal", 0) > 0.7:
                component_info.append("news")

            if component_info:
                reason += f" driven by {', '.join(component_info)}"

            return "BUY", confidence, reason

        elif signal < sell_threshold and has_position:
            reason = f"Strong sell signal ({signal:.2f})"

            # Add component strengths to reason
            component_info = []
            if components.get("technical_signal", 0) < 0.3:
                component_info.append("technical")
            if components.get("quantum_signal", 0) < 0.3:
                component_info.append("quantum")
            if components.get("news_signal", 0) < 0.3:
                component_info.append("news")
            if components.get("risk_signal", 0) < 0.3:
                component_info.append("risk")

            if component_info:
                reason += f" driven by {', '.join(component_info)}"

            return "SELL", confidence, reason

        else:
            if 0.4 <= signal <= 0.6:
                reason = "Neutral signal"
            elif signal > 0.6:
                reason = "Positive but below buy threshold"
            else:
                reason = "Negative but above sell threshold"

            return "HOLD", confidence, reason

    def get_quantum_adjustment_factors(self, symbol):
        """
        Get adjustment factors for quantum trading based on news and events

        These factors can be used to adjust quantum weights or feature importance
        based on current news sentiment and events

        Args:
            symbol (str): Stock symbol

        Returns:
            dict: Adjustment factors for quantum trading
        """
        try:
            # Get sentiment factors
            sentiment = self.news_collector.get_finance_sentiment_factors(symbol)

            # Get event risks
            event_risks = self.news_collector.analyze_event_risks([symbol])[symbol]

            # Get market risk
            market_risk = self.news_collector.get_market_risk_factors()

            # Calculate adjustment factors

            # 1. Volatility factor - higher during high risk/panic
            volatility_factor = 1 + (market_risk["panic_level"] / 100)

            # 2. Sentiment factor - scale from sentiment
            sentiment_factor = sentiment["combined_sentiment"] + 1  # Convert from [-1,1] to [0,2]

            # 3. Event impact factor - higher when events are detected
            event_impact = 1 + (event_risks["events_detected"] * 0.2)

            # 4. Trend consistency - how aligned are different signals
            signals = [
                sentiment["news_sentiment"],
                sentiment["social_sentiment"],
                sentiment["fear_greed_sentiment"]
            ]

            # Calculate standard deviation of signals
            signals_std = np.std(signals)
            trend_consistency = 1 - (signals_std * 2)  # Invert so higher = more consistent
            trend_consistency = max(0.5, min(2.0, trend_consistency))  # Limit range

            # Combine into a set of adjustment factors
            adjustment_factors = {
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "volatility_factor": float(volatility_factor),  # Higher during high risk
                "sentiment_factor": float(sentiment_factor),  # Higher with positive sentiment
                "event_impact": float(event_impact),  # Higher when events detected
                "trend_consistency": float(trend_consistency),  # Higher when signals agree
                "source_data": {
                    "news_sentiment": float(sentiment["news_sentiment"]),
                    "social_sentiment": float(sentiment["social_sentiment"]),
                    "fear_greed_sentiment": float(sentiment["fear_greed_sentiment"]),
                    "panic_level": float(market_risk["panic_level"]),
                    "event_count": event_risks["events_detected"]
                }
            }

            return adjustment_factors

        except Exception as e:
            logger.error(f"Error calculating quantum adjustment factors for {symbol}: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "volatility_factor": 1.0,
                "sentiment_factor": 1.0,
                "event_impact": 1.0,
                "trend_consistency": 1.0,
                "error": str(e)
            }

    def adjust_quantum_weights(self, symbol, base_weights, adjustment_factors=None):
        """
        Adjust quantum weights based on news and market factors

        Args:
            symbol (str): Stock symbol
            base_weights (list): Base quantum weights
            adjustment_factors (dict): Pre-calculated adjustment factors

        Returns:
            list: Adjusted quantum weights
        """
        if adjustment_factors is None:
            adjustment_factors = self.get_quantum_adjustment_factors(symbol)

        # Extract factors
        volatility_factor = adjustment_factors.get("volatility_factor", 1.0)
        sentiment_factor = adjustment_factors.get("sentiment_factor", 1.0)
        event_impact = adjustment_factors.get("event_impact", 1.0)
        trend_consistency = adjustment_factors.get("trend_consistency", 1.0)

        # Apply adjustments to each weight
        adjusted_weights = []

        for i, weight in enumerate(base_weights):
            # Different adjustment based on weight position
            if i < len(base_weights) // 3:
                # First third - adjust more by sentiment
                adj_weight = weight * sentiment_factor
            elif i < 2 * len(base_weights) // 3:
                # Middle third - adjust more by volatility
                adj_weight = weight * volatility_factor
            else:
                # Last third - adjust more by event impact
                adj_weight = weight * event_impact

            # Apply trend consistency to all weights
            adj_weight *= trend_consistency

            adjusted_weights.append(float(adj_weight))

        # Normalize to preserve sum
        total = sum(adjusted_weights)
        normalized_weights = [w / total * sum(base_weights) for w in adjusted_weights]

        return normalized_weights


def integrate_with_trading_bot(trading_bot_module=None):
    """
    Function to integrate this module with the trading bot

    Args:
        trading_bot_module: Trading bot module (if already imported)

    Returns:
        tuple: (news_integrator, patch_successful)
    """
    try:
        # Create the news integrator
        news_integrator = NewsIntegrator()

        # Import trading bot if not provided
        if trading_bot_module is None:
            try:
                import trading_bot
                trading_bot_module = trading_bot
            except ImportError:
                logger.error("Could not import trading_bot module")
                return news_integrator, False

        # Find make_trading_decision method in trading_bot
        original_make_trading_decision = None
        if hasattr(trading_bot_module, 'make_trading_decision'):
            original_make_trading_decision = trading_bot_module.make_trading_decision

        # Define enhanced decision function
        def enhanced_make_trading_decision(symbol, quantum_device, config):
            """Enhanced trading decision function with news integration"""
            logger.info(f"Making enhanced trading decision for {symbol} with news integration")

            # Call original function to get technical and quantum signals
            # Store original result for reference
            technical_signal = None
            quantum_signal = None

            # Extract signals from original function (implementation may vary based on trading_bot structure)
            try:
                # Get historical data
                historical_data = trading_bot_module.platform_adapter.get_market_data(symbol)

                # Get classical decision
                technical_signal = trading_bot_module.classical_decision(historical_data)

                # Get quantum prediction if available
                quantum_signal = None
                error_rate = None

                if trading_bot_module.QUANTUM_AVAILABLE and quantum_device is not None:
                    # Get quantum configuration
                    quantum_enabled = config.get("quantum_config", {}).get("enabled", True)
                    error_threshold = config.get("quantum_config", {}).get("error_threshold", 0.15)

                    # Estimate error rate
                    error_rate = trading_bot_module.estimate_quantum_error_rate(quantum_device)

                    if quantum_enabled and error_rate <= error_threshold:
                        # Get quantum prediction
                        quantum_result, confidence, actual_error = trading_bot_module.quantum_prediction(
                            symbol, historical_data, quantum_device, error_rate, config
                        )
                        quantum_signal = quantum_result
            except Exception as e:
                logger.error(f"Error getting original signals: {e}")
                technical_signal = 0.5  # Neutral

            # Default to neutral if we couldn't get signals
            if technical_signal is None:
                technical_signal = 0.5
            if quantum_signal is None:
                quantum_signal = technical_signal  # Use technical as fallback

            # Prepare signals for integration
            technical_signals = {symbol: technical_signal}
            quantum_signals = {symbol: quantum_signal}

            # Get integrated signals
            integrated_signals = news_integrator.get_integrated_signals(
                [symbol], technical_signals, quantum_signals
            )

            # Make trading decision based on integrated signal
            has_position = symbol in trading_bot_module.trade_history["positions"]
            decision, confidence, reason = news_integrator.make_trading_decision(
                symbol, integrated_signals[symbol],
                trading_bot_module.trade_history["positions"] if hasattr(trading_bot_module, 'trade_history') else None
            )

            # Log detailed decision
            logger.info(f"Trading decision for {symbol}: {decision} (confidence: {confidence:.2f})")
            logger.info(f"Reason: {reason}")

            # Execute trade if needed
            if decision == "BUY" and not has_position:
                logger.info(f"BUY signal for {symbol} based on integrated analysis")
                trading_bot_module.execute_trade("BUY", symbol)

            elif decision == "SELL" and has_position:
                logger.info(f"SELL signal for {symbol} based on integrated analysis")
                trading_bot_module.execute_trade("SELL", symbol)

            else:
                logger.info(f"HOLD signal for {symbol}")

            # Return the trading decision
            return decision, confidence, reason

        # Try to patch trading_bot module
        patch_successful = False
        try:
            if original_make_trading_decision is not None:
                # Save reference to original function
                trading_bot_module._original_make_trading_decision = original_make_trading_decision

                # Replace with enhanced function
                trading_bot_module.make_trading_decision = enhanced_make_trading_decision

                # Also adjust quantum weights using news data
                original_quantum_prediction = trading_bot_module.quantum_prediction

                def enhanced_quantum_prediction(symbol, historical_data, quantum_device, error_rate, config):
                    """Enhanced quantum prediction with news adjustment"""
                    # Get adjustment factors
                    adjustment_factors = news_integrator.get_quantum_adjustment_factors(symbol)

                    # Call original function
                    signal, confidence, actual_error = original_quantum_prediction(
                        symbol, historical_data, quantum_device, error_rate, config
                    )

                    # Adjust confidence based on news factors
                    trend_consistency = adjustment_factors.get("trend_consistency", 1.0)
                    adjusted_confidence = confidence * trend_consistency

                    # Adjust signal based on sentiment
                    sentiment_factor = adjustment_factors.get("sentiment_factor", 1.0)
                    sentiment_bias = (sentiment_factor - 1.0) * 0.1  # Scale to small adjustment
                    adjusted_signal = max(0, min(1, signal + sentiment_bias))

                    return adjusted_signal, adjusted_confidence, actual_error

                # Replace quantum prediction function
                trading_bot_module.quantum_prediction = enhanced_quantum_prediction

                logger.info("Successfully patched trading_bot module with news integration")
                patch_successful = True
            else:
                logger.warning("Could not find make_trading_decision function in trading_bot module")
        except Exception as e:
            logger.error(f"Error patching trading_bot module: {e}")

        return news_integrator, patch_successful
    except Exception as e:
        logger.error(f"Error in integrate_with_trading_bot: {e}")
        return NewsIntegrator(), False


def create_news_quantum_features(symbol, historical_data, news_integrator):
    """
    Create additional features for quantum models based on news data

    Args:
        symbol (str): Stock symbol
        historical_data (DataFrame): Historical price data
        news_integrator (NewsIntegrator): News integration instance

    Returns:
        list: Additional quantum features
    """
    # Get news sentiment data
    sentiment_factors = news_integrator.news_collector.get_finance_sentiment_factors(symbol)

    # Get market risk data
    market_risk = news_integrator.news_collector.get_market_risk_factors()

    # Calculate additional features
    features = []

    # 1. News sentiment (scaled to 0-1)
    news_sentiment = (sentiment_factors["news_sentiment"] + 1) / 2
    features.append(news_sentiment)

    # 2. Social sentiment (scaled to 0-1)
    social_sentiment = (sentiment_factors["social_sentiment"] + 1) / 2
    features.append(social_sentiment)

    # 3. Market fear/greed (scaled to 0-1)
    fear_greed = market_risk["fear_greed_score"] / 100
    features.append(fear_greed)

    # 4. Event risk (inverse - higher is less risk)
    event_risks = news_integrator.news_collector.analyze_event_risks([symbol])[symbol]
    event_risk_factor = max(0, min(1, 1 - (event_risks["risk_score"] / 10)))
    features.append(event_risk_factor)

    # 5. Panic level (inverse - higher is less panic)
    panic_factor = 1 - (market_risk["panic_level"] / 100)
    features.append(panic_factor)

    # Ensure all features are floats and in range [0,1]
    features = [float(max(0, min(1, f))) for f in features]

    return features


if __name__ == "__main__":
    # Test integration
    news_integrator = NewsIntegrator()

    # Test symbols
    symbols = ["AAPL", "MSFT", "NVDA"]

    # Update sentiment data
    news_integrator.update_sentiment_data(symbols)

    # Simulate technical and quantum signals
    technical_signals = {
        "AAPL": 0.65,
        "MSFT": 0.78,
        "NVDA": 0.42
    }

    quantum_signals = {
        "AAPL": 0.71,
        "MSFT": 0.67,
        "NVDA": 0.48
    }

    # Get integrated signals
    integrated_signals = news_integrator.get_integrated_signals(
        symbols, technical_signals, quantum_signals
    )

    # Print integrated signals
    for symbol, signal_data in integrated_signals.items():
        print(f"{symbol} Integrated Signal: {signal_data['integrated_signal']:.4f}")

        decision, confidence, reason = news_integrator.make_trading_decision(
            symbol, signal_data
        )

        print(f"Decision: {decision} (confidence: {confidence:.2f})")
        print(f"Reason: {reason}")
        print()
