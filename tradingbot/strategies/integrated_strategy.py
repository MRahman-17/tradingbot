import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import os
import json

logger = logging.getLogger(__name__)


class IntegratedStrategy:
    """Integrated trading strategy combining technical, quantum, and news analysis"""

    def __init__(self, config: Dict[str, Any],
                 technical_analyzer=None,
                 quantum_analyzer=None,
                 news_collector=None,
                 compliance_checker=None) -> None:
        """Initialize integrated strategy with components

        Args:
            config: Strategy configuration
            technical_analyzer: Technical analysis component
            quantum_analyzer: Quantum analysis component
            news_collector: News collection component
            compliance_checker: Halal compliance component
        """
        self.config = config
        self.technical_analyzer = technical_analyzer
        self.quantum_analyzer = quantum_analyzer
        self.news_collector = news_collector
        self.compliance_checker = compliance_checker

        # Default weights for integration
        self.integration_weights = {
            "technical": 0.40,  # Technical analysis weight
            "quantum": 0.25,  # Quantum analysis weight
            "news": 0.25,  # News sentiment weight
            "market_risk": 0.10  # Market risk factors weight
        }

        # Load trade history
        self.trade_history = self._load_trade_history()

        # Create required directories
        os.makedirs("data/integrated_signals", exist_ok=True)

        logger.info("Integrated strategy initialized")

    def _load_trade_history(self) -> Dict[str, Any]:
        """Load trade history from file

        Returns:
            Trade history dictionary
        """
        try:
            if os.path.exists("data/trade_history.json"):
                with open("data/trade_history.json", "r") as f:
                    trade_history = json.load(f)
                    logger.info("Trade history loaded")
                    return trade_history
            else:
                logger.info("No trade history found, using empty")
        except Exception as e:
            logger.error(f"Error loading trade history: {e}")

        return {"positions": {}, "trades": []}

    def save_trade_history(self) -> None:
        """Save trade history to file"""
        try:
            os.makedirs("data", exist_ok=True)
            with open("data/trade_history.json", "w") as f:
                json.dump(self.trade_history, f, indent=4)
                logger.info("Trade history saved")
        except Exception as e:
            logger.error(f"Error saving trade history: {e}")

    def get_integrated_signal(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get integrated trading signal for a symbol

        Args:
            symbol: Stock symbol
            market_data: Market data for the symbol

        Returns:
            Dictionary with integrated signal and details
        """
        try:
            start_time = time.time()

            # Calculate technical signal
            technical_signal = 0.5  # Neutral default
            if self.technical_analyzer:
                # Calculate indicators if not already present
                if 'RSI' not in market_data.columns:
                    market_data = self.technical_analyzer.calculate_indicators(market_data)

                technical_signal = self.technical_analyzer.get_technical_signal(market_data)
                logger.info(f"Technical signal for {symbol}: {technical_signal:.4f}")

            # Get news sentiment
            news_data = None
            news_signal = 0.5  # Neutral default
            if self.news_collector:
                sentiment_factors = self.news_collector.get_finance_sentiment_factors(symbol)
                news_signal = sentiment_factors.get("sentiment_signal", 0.5)
                news_data = sentiment_factors
                logger.info(f"News signal for {symbol}: {news_signal:.4f}")

            # Get market risk
            risk_factors = None
            risk_signal = 0.5  # Neutral default
            if self.news_collector:
                risk_factors = self.news_collector.get_market_risk_factors()
                panic_level = risk_factors.get("panic_level", 50)
                # Scale risk score to a 0-1 signal (higher risk = lower signal)
                risk_signal = max(0, min(1, 1 - (panic_level / 100)))
                logger.info(f"Market risk signal: {risk_signal:.4f} (panic: {panic_level})")

            # Calculate quantum signal
            quantum_signal = 0.5  # Neutral default
            quantum_confidence = 0.0
            if self.quantum_analyzer and self.config.get("quantum", {}).get("enabled", True):
                quantum_signal, quantum_confidence = self.quantum_analyzer.get_quantum_prediction(
                    symbol, market_data, news_data
                )
                logger.info(f"Quantum signal for {symbol}: {quantum_signal:.4f} (confidence: {quantum_confidence:.4f})")

            # Calculate integrated signal
            # Adjust weights based on confidence levels
            adjusted_weights = self.integration_weights.copy()

            # If quantum confidence is high, increase quantum weight
            if quantum_confidence > 0.8:
                # Increase quantum weight by up to 0.1 based on confidence
                quantum_boost = 0.1 * ((quantum_confidence - 0.8) / 0.2)
                adjusted_weights["quantum"] += quantum_boost

                # Reduce other weights proportionally
                total_other = adjusted_weights["technical"] + adjusted_weights["news"] + adjusted_weights["market_risk"]
                if total_other > 0:
                    ratio = (total_other - quantum_boost) / total_other
                    adjusted_weights["technical"] *= ratio
                    adjusted_weights["news"] *= ratio
                    adjusted_weights["market_risk"] *= ratio

            # Adjust weights based on market conditions
            if risk_factors and "panic_level" in risk_factors:
                panic_level = risk_factors["panic_level"]

                if panic_level >= 75:
                    # In high panic, increase weight of news and market risk
                    adjusted_weights["news"] += 0.1
                    adjusted_weights["market_risk"] += 0.1
                    adjusted_weights["technical"] -= 0.15
                    adjusted_weights["quantum"] -= 0.05
                elif panic_level <= 25:
                    # In low panic/high greed, increase weight of quantum
                    adjusted_weights["quantum"] += 0.1
                    adjusted_weights["news"] -= 0.05
                    adjusted_weights["market_risk"] -= 0.05

            # Normalize weights to sum to 1
            total = sum(adjusted_weights.values())
            for key in adjusted_weights:
                adjusted_weights[key] /= total

            # Calculate integrated signal
            integrated_signal = (
                    technical_signal * adjusted_weights["technical"] +
                    quantum_signal * adjusted_weights["quantum"] +
                    news_signal * adjusted_weights["news"] +
                    risk_signal * adjusted_weights["market_risk"]
            )

            # Log integration details
            logger.info(f"Integrated signal for {symbol}: {integrated_signal:.4f}")
            logger.info(f"Integration weights - Technical: {adjusted_weights['technical']:.2f}, " +
                        f"Quantum: {adjusted_weights['quantum']:.2f}, News: {adjusted_weights['news']:.2f}, " +
                        f"Market Risk: {adjusted_weights['market_risk']:.2f}")

            # Record the integrated signal and components
            result = {
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "integrated_signal": float(integrated_signal),
                "components": {
                    "technical_signal": float(technical_signal),
                    "quantum_signal": float(quantum_signal),
                    "news_signal": float(news_signal),
                    "risk_signal": float(risk_signal)
                },
                "weights": adjusted_weights,
                "confidences": {
                    "quantum": float(quantum_confidence),
                    "technical": 0.8  # Default technical confidence
                },
                "market_risk_level": risk_factors.get("risk_level", "Unknown") if risk_factors else "Unknown",
                "computation_time": time.time() - start_time
            }

            # Save integrated signal
            self._save_integrated_signal(symbol, result)

            return result
        except Exception as e:
            logger.error(f"Error calculating integrated signal for {symbol}: {e}")
            # Provide a neutral signal on error
            return {
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "integrated_signal": 0.5,
                "error": str(e)
            }

    def _save_integrated_signal(self, symbol: str, signal_data: Dict[str, Any]) -> None:
        """Save integrated signal to file

        Args:
            symbol: Stock symbol
            signal_data: Integrated signal data
        """
        try:
            # Save to file with timestamp
            filename = f"data/integrated_signals/{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(signal_data, f, indent=4)

            # Also save as latest
            with open(f"data/integrated_signals/{symbol}_latest.json", 'w') as f:
                json.dump(signal_data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving integrated signal for {symbol}: {e}")

    def make_trading_decision(self, symbol: str, signal_data: Dict[str, Any]) -> Tuple[str, float, str]:
        """Make a trading decision based on integrated signal

        Args:
            symbol: Stock symbol
            signal_data: Integrated signal data

        Returns:
            Tuple of (decision, confidence, reason)
        """
        # Check if we have an error
        if "error" in signal_data:
            return "HOLD", 0.5, f"Error in signal integration: {signal_data['error']}"

        # Extract the signal and components
        signal = signal_data["integrated_signal"]
        components = signal_data.get("components", {})

        # Check if we have a position
        has_position = symbol in self.trade_history["positions"]

        # Define thresholds
        buy_threshold = 0.7
        sell_threshold = 0.3

        # Additional factors
        market_risk = signal_data.get("market_risk_level", "Unknown")

        # Calculate decision confidence
        confidence = abs((signal - 0.5) * 2)  # 0 to 1 scale

        # Check compliance if required
        if self.config.get("trading", {}).get("halal_compliance", False) and self.compliance_checker:
            compliance_result = self.compliance_checker.check_compliance(symbol)
            if not compliance_result.get("compliant", False):
                if has_position:
                    return "SELL", 0.9, f"Stock {symbol} is not Halal compliant"
                else:
                    return "HOLD", 0.9, f"Stock {symbol} is not Halal compliant"

        # Special cases first
        if "Extreme Risk" in market_risk and has_position:
            return "SELL", max(0.7, confidence), "Extreme market risk detected"

        # Check if minimum hold period has passed
        if has_position and not self._can_sell_due_to_hold_period(symbol):
            return "HOLD", confidence, "Minimum hold period not met"

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

    def _can_sell_due_to_hold_period(self, symbol: str) -> bool:
        """Check if a stock can be sold based on minimum hold period

        Args:
            symbol: Stock symbol

        Returns:
            True if minimum hold period has passed, False otherwise
        """
        if symbol not in self.trade_history["positions"]:
            return False

        position = self.trade_history["positions"][symbol]
        entry_time_str = position.get("entry_time", "")

        if not entry_time_str:
            return True  # No entry time recorded, assume hold period passed

        try:
            # Parse entry time
            entry_time = datetime.fromisoformat(entry_time_str)
            current_time = datetime.now()

            # Get min hold period from config (default to 48 hours if not specified)
            min_hold_seconds = self.config.get("trading", {}).get("min_hold_period", 172800)
            min_hold_period = timedelta(seconds=min_hold_seconds)

            # Check if minimum hold period has passed
            time_held = current_time - entry_time
            can_sell = time_held >= min_hold_period

            if not can_sell:
                hours_left = (min_hold_period - time_held).total_seconds() / 3600
                logger.info(
                    f"Cannot sell {symbol} yet - minimum hold period not met. {hours_left:.1f} hours remaining.")

            return can_sell
        except Exception as e:
            logger.error(f"Error checking hold period for {symbol}: {e}")
            return True  # On error, assume hold period passed

    def execute_trade(self, action: str, symbol: str, platform_adapter, quantity: int = 1) -> bool:
        """Execute a trade

        Args:
            action: Trade action ('BUY' or 'SELL')
            symbol: Stock symbol
            platform_adapter: Trading platform adapter
            quantity: Trade quantity

        Returns:
            True if trade succeeded, False otherwise
        """
        if action.upper() not in ["BUY", "SELL"]:
            logger.error(f"Invalid trade action: {action}")
            return False

        try:
            # Check if we already have a position for BUY
            if action.upper() == "BUY" and symbol in self.trade_history["positions"]:
                logger.info(f"Already have a position in {symbol}")
                return False

            # Check if we have a position for SELL
            if action.upper() == "SELL" and symbol not in self.trade_history["positions"]:
                logger.info(f"No position in {symbol} to sell")
                return False

            # Get position details for SELL
            entry_price = None
            if action.upper() == "SELL" and symbol in self.trade_history["positions"]:
                position = self.trade_history["positions"][symbol]
                entry_price = position.get("entry_price")
                quantity = position.get("quantity", quantity)

            # Get current price
            current_price = platform_adapter.get_price(symbol)
            if current_price is None:
                logger.error(f"Could not get price for {symbol}")
                return False

            # Place order
            order_id = platform_adapter.place_order(
                symbol=symbol,
                side=action.lower(),
                quantity=quantity
            )

            if not order_id:
                logger.error(f"Failed to place {action} order for {symbol}")
                return False

            # Record the trade
            if action.upper() == "BUY":
                # Record the position
                self.trade_history["positions"][symbol] = {
                    "entry_price": current_price,
                    "quantity": quantity,
                    "entry_time": datetime.now().isoformat(),
                    "order_id": order_id
                }

                # Record the trade
                self.trade_history["trades"].append({
                    "symbol": symbol,
                    "action": "BUY",
                    "quantity": quantity,
                    "price": current_price,
                    "timestamp": datetime.now().isoformat(),
                    "order_id": order_id
                })

                logger.info(f"BUY order executed: {quantity} shares of {symbol} at ${current_price:.2f}")
            else:  # SELL
                # Calculate profit/loss
                profit_loss = None
                profit_loss_pct = None

                if entry_price is not None:
                    profit_loss = (current_price - entry_price) * quantity
                    profit_loss_pct = (current_price / entry_price - 1) * 100

                # Record the trade
                trade_record = {
                    "symbol": symbol,
                    "action": "SELL",
                    "quantity": quantity,
                    "price": current_price,
                    "timestamp": datetime.now().isoformat(),
                    "order_id": order_id
                }

                if profit_loss is not None:
                    trade_record["profit_loss"] = profit_loss
                    trade_record["profit_loss_pct"] = profit_loss_pct

                self.trade_history["trades"].append(trade_record)

                # Remove the position
                del self.trade_history["positions"][symbol]

                # Update quantum prediction accuracy if applicable
                if self.quantum_analyzer:
                    was_correct = profit_loss > 0 if profit_loss is not None else None
                    if was_correct is not None:
                        self.quantum_analyzer.update_prediction_accuracy(
                            symbol, was_correct, profit_loss
                        )

                        # Periodically update quantum model
                        self.quantum_analyzer.update_quantum_model(symbol)

                if profit_loss is not None:
                    logger.info(f"SELL order executed: {quantity} shares of {symbol} at ${current_price:.2f} " +
                                f"(P&L: ${profit_loss:.2f}, {profit_loss_pct:.2f}%)")
                else:
                    logger.info(f"SELL order executed: {quantity} shares of {symbol} at ${current_price:.2f}")

            # Save trade history
            self.save_trade_history()

            return True
        except Exception as e:
            logger.error(f"Error executing {action} trade for {symbol}: {e}")
            return False

    def save_performance_metrics(self) -> Dict[str, Any]:
        """Calculate and save performance metrics

        Returns:
            Dictionary of performance metrics
        """
        try:
            trades = self.trade_history["trades"]
            if not trades:
                logger.info("No trades to analyze")
                return {}

            # Calculate metrics
            sell_trades = [t for t in trades if t["action"] == "SELL" and "profit_loss" in t]
            if not sell_trades:
                logger.info("No completed trades to analyze")
                return {}

            # Calculate performance metrics
            total_profit = sum(t.get("profit_loss", 0) for t in sell_trades)
            avg_profit = total_profit / len(sell_trades)
            avg_profit_pct = sum(t.get("profit_loss_pct", 0) for t in sell_trades) / len(sell_trades)

            winning_trades = sum(1 for t in sell_trades if t.get("profit_loss", 0) > 0)
            win_rate = winning_trades / len(sell_trades)

            # Calculate max drawdown
            equity_curve = []
            current_equity = 10000  # Start with $10,000
            for trade in trades:
                if trade["action"] == "SELL" and "profit_loss" in trade:
                    current_equity += trade.get("profit_loss", 0)
                equity_curve.append(current_equity)

            if equity_curve:
                max_equity = equity_curve[0]
                max_drawdown = 0
                for equity in equity_curve:
                    max_equity = max(max_equity, equity)
                    drawdown = (max_equity - equity) / max_equity * 100
                    max_drawdown = max(max_drawdown, drawdown)
            else:
                max_drawdown = 0

            # Include quantum metrics if available
            quantum_accuracy = None
            if self.quantum_analyzer and self.quantum_analyzer.prediction_history:
                completed_preds = [p for p in self.quantum_analyzer.prediction_history if p["correct"] is not None]
                if completed_preds:
                    correct_predictions = sum(1 for p in completed_preds if p["correct"])
                    quantum_accuracy = correct_predictions / len(completed_preds)

            # Save metrics
            metrics = {
                "date": datetime.now().isoformat(),
                "total_trades": len(sell_trades),
                "winning_trades": winning_trades,
                "win_rate": win_rate,
                "total_profit": float(total_profit),
                "avg_profit": float(avg_profit),
                "avg_profit_pct": float(avg_profit_pct),
                "max_drawdown": float(max_drawdown),
                "quantum_accuracy": quantum_accuracy
            }

            # Create metrics file
            os.makedirs("data/performance", exist_ok=True)
            metrics_path = "data/performance/metrics.json"

            # Load existing or create new
            all_metrics = []
            if os.path.exists(metrics_path):
                try:
                    with open(metrics_path, "r") as f:
                        all_metrics = json.load(f)
                except Exception:
                    all_metrics = []

            all_metrics.append(metrics)

            # Save metrics
            with open(metrics_path, "w") as f:
                json.dump(all_metrics, f, indent=4)

            logger.info(f"Performance metrics saved: {winning_trades}/{len(sell_trades)} winning trades")

            if quantum_accuracy is not None:
                logger.info(f"Quantum prediction accuracy: {quantum_accuracy:.2f}")

            return metrics
        except Exception as e:
            logger.error(f"Error saving performance metrics: {e}")
            return {}


