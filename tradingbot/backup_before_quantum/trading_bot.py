#!/usr/bin/env python3
"""
Trading Bot for automated trading with WebUll integration.
"""
import os
import sys
import time
import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Trading Bot")

# Default configuration
DEFAULT_CONFIG = {
    "trading_bot": {
        "enabled": True,
        "symbols": ["AAPL", "MSFT", "GOOGL"],
        "max_drawdown": 0.05,
        "kelly_fraction": 0.02,
        "quantity": 1,
        "min_hold_period": 172800,  # 48 hours in seconds
        "sleep_time": 60,
        "halal_compliance": True
    },
    "platform": {
        "name": "mock",  # Using mock platform for testing
        "use_paper_trading": True
    }
}

# Trading parameters
symbols = DEFAULT_CONFIG["trading_bot"]["symbols"]
sleep_time = DEFAULT_CONFIG["trading_bot"]["sleep_time"]


# Create a simple mock adapter for testing
class MockAdapter:
    def __init__(self):
        self.positions = {}
        self.prices = {
            "AAPL": 175.0,
            "MSFT": 350.0,
            "GOOGL": 141.0
        }
        self.order_id = 1000
        logger.info("Mock adapter initialized")

    def get_price(self, symbol):
        """Get current price with some random movement"""
        price = self.prices.get(symbol, 100.0)
        # Add some random movement
        self.prices[symbol] = price * (1 + random.uniform(-0.01, 0.01))
        return self.prices[symbol]

    def get_positions(self):
        """Get current positions"""
        positions = []
        for symbol, details in self.positions.items():
            current_price = self.get_price(symbol)
            entry_price = details["entry_price"]
            quantity = details["quantity"]

            # Calculate P&L
            unrealized_pl = (current_price - entry_price) * quantity
            unrealized_pl_pct = (current_price / entry_price - 1) * 100

            positions.append({
                "symbol": symbol,
                "quantity": quantity,
                "entry_price": entry_price,
                "current_price": current_price,
                "unrealized_pl": unrealized_pl,
                "unrealized_pl_percent": unrealized_pl_pct
            })

        return positions

    def place_order(self, symbol, side, quantity):
        """Place a mock order"""
        self.order_id += 1
        current_price = self.get_price(symbol)

        if side.lower() == "buy":
            self.positions[symbol] = {
                "entry_price": current_price,
                "quantity": quantity
            }
            logger.info(f"BUY order for {quantity} shares of {symbol} at ${current_price:.2f}")
        elif side.lower() == "sell":
            if symbol in self.positions:
                del self.positions[symbol]
                logger.info(f"SELL order for {quantity} shares of {symbol} at ${current_price:.2f}")
            else:
                logger.warning(f"Cannot sell {symbol} - no position")
                return None

        return self.order_id


# Initialize the trading platform adapter
platform_adapter = MockAdapter()

# Simple trade history storage
trade_history = {
    "positions": {},
    "trades": []
}


def load_trade_history():
    """Load trade history from file"""
    global trade_history
    try:
        if os.path.exists("data/trade_history.json"):
            with open("data/trade_history.json", "r") as f:
                trade_history = json.load(f)
                logger.info("Trade history loaded")
        else:
            logger.info("No trade history found, using empty")
    except Exception as e:
        logger.error(f"Error loading trade history: {e}")


def save_trade_history():
    """Save trade history to file"""
    try:
        os.makedirs("data", exist_ok=True)
        with open("data/trade_history.json", "w") as f:
            json.dump(trade_history, f, indent=4)
            logger.info("Trade history saved")
    except Exception as e:
        logger.error(f"Error saving trade history: {e}")


def make_trading_decision(symbol):
    """Simple trading decision logic"""
    # Random decision for demo
    signal = random.random()

    # Check if we have a position
    has_position = symbol in trade_history["positions"]

    if signal > 0.7 and not has_position:
        logger.info(f"BUY signal for {symbol} (score: {signal:.4f})")
        execute_trade("BUY", symbol)
    elif signal < 0.3 and has_position:
        logger.info(f"SELL signal for {symbol} (score: {signal:.4f})")
        execute_trade("SELL", symbol)
    else:
        logger.info(f"HOLD signal for {symbol} (score: {signal:.4f})")


def execute_trade(action, symbol):
    """Execute a trade"""
    global trade_history

    quantity = 1  # Fixed quantity for simplicity

    if action.upper() == "BUY":
        # Check if we already have a position
        if symbol in trade_history["positions"]:
            logger.info(f"Already have a position in {symbol}")
            return

        # Get current price
        current_price = platform_adapter.get_price(symbol)

        # Place order
        order_id = platform_adapter.place_order(symbol, "buy", quantity)

        if order_id:
            # Record the position
            trade_history["positions"][symbol] = {
                "entry_price": current_price,
                "quantity": quantity,
                "entry_time": time.time(),
                "order_id": order_id
            }

            # Record the trade
            trade_history["trades"].append({
                "symbol": symbol,
                "action": "BUY",
                "quantity": quantity,
                "price": current_price,
                "timestamp": datetime.now().isoformat(),
                "order_id": order_id
            })

            # Save trade history
            save_trade_history()

    elif action.upper() == "SELL":
        # Check if we have a position
        if symbol not in trade_history["positions"]:
            logger.info(f"No position in {symbol} to sell")
            return

        # Get position details
        position = trade_history["positions"][symbol]
        entry_price = position["entry_price"]
        quantity = position["quantity"]

        # Get current price
        current_price = platform_adapter.get_price(symbol)

        # Place order
        order_id = platform_adapter.place_order(symbol, "sell", quantity)

        if order_id:
            # Calculate profit/loss
            profit_loss = (current_price - entry_price) * quantity
            profit_loss_pct = (current_price / entry_price - 1) * 100

            # Record the trade
            trade_history["trades"].append({
                "symbol": symbol,
                "action": "SELL",
                "quantity": quantity,
                "price": current_price,
                "profit_loss": profit_loss,
                "profit_loss_pct": profit_loss_pct,
                "timestamp": datetime.now().isoformat(),
                "order_id": order_id
            })

            # Remove the position
            del trade_history["positions"][symbol]

            # Save trade history
            save_trade_history()

            logger.info(f"SELL completed: P&L ${profit_loss:.2f} ({profit_loss_pct:.2f}%)")


def save_performance_metrics():
    """Save basic performance metrics"""
    try:
        trades = trade_history["trades"]
        if not trades:
            logger.info("No trades to analyze")
            return

        # Calculate metrics
        sell_trades = [t for t in trades if t["action"] == "SELL"]
        if not sell_trades:
            logger.info("No completed trades to analyze")
            return

        # Calculate performance metrics
        total_profit = sum(t.get("profit_loss", 0) for t in sell_trades)
        avg_profit = total_profit / len(sell_trades)

        winning_trades = sum(1 for t in sell_trades if t.get("profit_loss", 0) > 0)
        win_rate = winning_trades / len(sell_trades)

        # Save metrics
        metrics = {
            "date": datetime.now().isoformat(),
            "total_trades": len(sell_trades),
            "winning_trades": winning_trades,
            "win_rate": win_rate,
            "total_profit": float(total_profit),
            "avg_profit": float(avg_profit)
        }

        # Create metrics file
        os.makedirs("data/performance", exist_ok=True)
        metrics_path = "data/performance/metrics.json"

        # Load existing or create new
        if os.path.exists(metrics_path):
            try:
                with open(metrics_path, "r") as f:
                    all_metrics = json.load(f)
            except:
                all_metrics = []
        else:
            all_metrics = []

        all_metrics.append(metrics)

        # Save metrics
        with open(metrics_path, "w") as f:
            json.dump(all_metrics, f, indent=4)

        logger.info(f"Performance metrics saved: {winning_trades}/{len(sell_trades)} winning trades")

    except Exception as e:
        logger.error(f"Error saving performance metrics: {e}")


def trading_loop():
    """Main trading loop"""
    logger.info("Trading bot starting")

    # Load trade history
    load_trade_history()

    try:
        while True:
            logger.info("Starting trading cycle")

            # Check if it's market hours (simplified)
            now = datetime.now()
            is_market_hours = (
                    0 <= now.weekday() <= 4 and  # Monday to Friday
                    9 <= now.hour < 16  # 9 AM to 4 PM
            )

            if is_market_hours:
                # Process each symbol
                for symbol in symbols:
                    try:
                        logger.info(f"Processing {symbol}")
                        make_trading_decision(symbol)
                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {e}")

                # Save performance metrics
                save_performance_metrics()
            else:
                logger.info("Market is closed, waiting...")

            # Sleep before next cycle
            logger.info(f"Sleeping for {sleep_time} seconds")
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        logger.info("Trading bot stopped by user")
    except Exception as e:
        logger.error(f"Trading bot error: {e}")

    logger.info("Trading bot shutdown")


if __name__ == "__main__":
    trading_loop()
