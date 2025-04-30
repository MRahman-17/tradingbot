import logging
import json
import os
import numpy as np
from datetime import datetime

logger = logging.getLogger("Adaptive Weights")


class WeightManager:
    def __init__(self):
        self.weights_history = []
        self.load_weights_history()

    def load_weights_history(self):
        """Load historical weights data"""
        weights_path = "data/weights/weights_history.json"

        if os.path.exists(weights_path):
            try:
                with open(weights_path, 'r') as f:
                    self.weights_history = json.load(f)
                logger.info("Weights history loaded")
            except Exception as e:
                logger.error(f"Error loading weights history: {e}")
                self.weights_history = []

    def save_weights_history(self):
        """Save weights history to file"""
        weights_path = "data/weights/weights_history.json"
        os.makedirs(os.path.dirname(weights_path), exist_ok=True)

        try:
            with open(weights_path, 'w') as f:
                json.dump(self.weights_history, f, indent=4)
            logger.info("Weights history saved")
        except Exception as e:
            logger.error(f"Error saving weights history: {e}")

    def get_market_regime_weights(self, market_condition):
        """Adjust weights based on current market regime"""
        if market_condition == "high_volatility":
            # During high volatility, increase news weight
            return {"technical": 0.35, "quantum": 0.20, "news": 0.35, "market_risk": 0.10}
        elif market_condition == "trending":
            # In trending markets, technical analysis often works better
            return {"technical": 0.50, "quantum": 0.25, "news": 0.15, "market_risk": 0.10}
        elif market_condition == "low_volatility":
            # In calm markets, balanced approach
            return {"technical": 0.40, "quantum": 0.30, "news": 0.20, "market_risk": 0.10}
        else:
            # Default weights for normal markets
            return {"technical": 0.40, "quantum": 0.25, "news": 0.25, "market_risk": 0.10}

    def detect_market_regime(self, market_data):
        """Detect current market regime based on market data"""
        # A simple approach using volatility and trend strength

        # Calculate recent volatility (standard deviation of returns)
        returns = np.diff(market_data['Close']) / market_data['Close'][:-1]
        recent_volatility = np.std(returns[-20:])  # 20-day volatility

        # Calculate trend strength
        sma_20 = market_data['Close'].rolling(20).mean().iloc[-1]
        sma_50 = market_data['Close'].rolling(50).mean().iloc[-1]

        trend_strength = abs((sma_20 / sma_50) - 1)

        # Determine regime
        if recent_volatility > 0.025:  # High volatility threshold
            return "high_volatility"
        elif trend_strength > 0.05:  # Strong trend threshold
            return "trending"
        elif recent_volatility < 0.01:  # Low volatility threshold
            return "low_volatility"
        else:
            return "normal"

    def adjust_integration_weights(self, symbol, historical_performance):
        """Dynamically adjust weights based on historical accuracy"""
        # Calculate accuracy for each signal type
        technical_accuracy = historical_performance.get('technical_accuracy', 0.5)
        quantum_accuracy = historical_performance.get('quantum_accuracy', 0.5)
        news_accuracy = historical_performance.get('news_accuracy', 0.5)

        # Normalize to ensure weights sum to 1
        total_accuracy = technical_accuracy + quantum_accuracy + news_accuracy

        # Set minimum weight threshold to prevent any signal from being ignored
        min_weight = 0.15

        # Calculate initial weights based on accuracy
        weights = {
            "technical": max(min_weight, technical_accuracy / total_accuracy),
            "quantum": max(min_weight, quantum_accuracy / total_accuracy),
            "news": max(min_weight, news_accuracy / total_accuracy)
        }

        # Renormalize
        total = sum(weights.values())
        for key in weights:
            weights[key] /= total

        # Add market risk weight
        weights["market_risk"] = 0.10

        # Renormalize again
        total = sum(weights.values())
        for key in weights:
            weights[key] /= total

        return weights

    def get_integrated_signal(self, symbol, signals, confidences, market_data, historical_performance=None):
        """Get integrated signal with dynamic weighting"""
        # Detect current market regime
        market_regime = self.detect_market_regime(market_data)

        # Get regime-based weights
        base_weights = self.get_market_regime_weights(market_regime)

        # Adjust based on historical performance if available
        if historical_performance:
            performance_weights = self.adjust_integration_weights(symbol, historical_performance)

            # Average the two weight approaches (50% regime, 50% performance)
            adjusted_weights = {}
            for key in base_weights:
                adjusted_weights[key] = 0.5 * base_weights[key] + 0.5 * performance_weights.get(key, 0)
        else:
            adjusted_weights = base_weights

        # Apply confidence levels
        final_weights = {}
        for signal_type, weight in adjusted_weights.items():
            confidence = confidences.get(signal_type, 0.5)
            # Scale weight by confidence
            final_weights[signal_type] = weight * confidence

        # Normalize weights
        total_weight = sum(final_weights.values())
        for key in final_weights:
            final_weights[key] /= total_weight

        # Calculate weighted signal
        integrated_signal = sum(signals[key] * final_weights[key] for key in final_weights)

        # Record the weights used
        weight_record = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "market_regime": market_regime,
            "weights": final_weights,
            "integrated_signal": float(integrated_signal)
        }
        self.weights_history.append(weight_record)

        # Periodically save weights history (limit history size)
        if len(self.weights_history) % 10 == 0:
            # Keep only the last 1000 records
            if len(self.weights_history) > 1000:
                self.weights_history = self.weights_history[-1000:]
            self.save_weights_history()

        return integrated_signal, final_weights
