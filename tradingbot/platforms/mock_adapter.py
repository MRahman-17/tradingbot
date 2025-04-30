import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from platforms.platform_base import PlatformAdapter

logger = logging.getLogger(__name__)


class MockAdapter(PlatformAdapter):
    """Mock adapter for simulating trading with realistic market data"""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize mock adapter with configuration

        Args:
            config: Platform configuration
        """
        super().__init__(config)
        self.name = "mock"
        self.authenticated = True
        self.positions = {}
        self.prices = {
            "AAPL": 175.0,
            "MSFT": 350.0,
            "NVDA": 141.0
        }
        self.order_id = 1000
        self.orders = {}
        self.market_data = {}

        # Initialize with some simulated historical data
        self._initialize_market_data()

        logger.info("Mock adapter initialized")

    def login(self) -> bool:
        """Authenticate with the mock platform

        Returns:
            Always returns True for mock adapter
        """
        self.authenticated = True
        logger.info("Mock login successful")
        return True

    def logout(self) -> bool:
        """Logout from the mock platform

        Returns:
            Always returns True for mock adapter
        """
        self.authenticated = False
        logger.info("Mock logout successful")
        return True

    def _initialize_market_data(self) -> None:
        """Create realistic simulated market data with trends and patterns"""
        for symbol in self.prices.keys():
            # Generate 90 days of realistic data
            days = 90
            base_price = self.prices[symbol]

            # Create time series with realistic properties
            # Start with random walk
            random_walk = np.random.normal(0, 0.015, days).cumsum()

            # Add trend component
            trend = np.linspace(0, 0.2, days) if symbol in ["AAPL", "MSFT"] else np.linspace(0, -0.1, days)

            # Add cyclical component (weekly pattern)
            cyclical = 0.02 * np.sin(np.linspace(0, 6 * np.pi, days))

            # Combine components
            price_series = base_price * (1 + random_walk + trend + cyclical)

            # Create realistic volume
            volume = np.random.randint(1000000, 10000000, days)

            # Create dataframe with OHLCV data
            dates = pd.date_range(end=datetime.now(), periods=days)
            df = pd.DataFrame({
                'Date': dates,
                'Open': price_series * (1 - np.random.uniform(0, 0.01, days)),
                'High': price_series * (1 + np.random.uniform(0, 0.02, days)),
                'Low': price_series * (1 - np.random.uniform(0, 0.02, days)),
                'Close': price_series,
                'Volume': volume
            })

            # Set date as index
            df.set_index('Date', inplace=True)

            # Set the current price to the last close
            self.prices[symbol] = float(df['Close'].iloc[-1])

            # Store the dataframe
            self.market_data[symbol] = df

    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price with some realistic movement

        Args:
            symbol: Stock symbol

        Returns:
            Current price or None if symbol not found
        """
        if symbol not in self.prices:
            if symbol in ["SPY", "QQQ", "DIA"]:  # Common symbols we might want to support
                self.prices[symbol] = 400.0 if symbol == "SPY" else 350.0 if symbol == "QQQ" else 320.0
            else:
                logger.warning(f"Price not found for symbol {symbol}")
                return None

        price = self.prices[symbol]
        # Add some random movement with momentum
        change = np.random.normal(0, 0.01)
        # Add momentum (prices tend to continue in the same direction)
        if symbol in self.market_data:
            df = self.market_data[symbol]
            if len(df) >= 2:
                last_change = (df['Close'].iloc[-1] / df['Close'].iloc[-2]) - 1
                change = change + (last_change * 0.3)  # 30% momentum factor

        self.prices[symbol] = price * (1 + change)

        # Update the market data
        if symbol in self.market_data:
            new_row = pd.DataFrame({
                'Open': [price],
                'High': [price * (1 + max(0, change * 1.5))],
                'Low': [price * (1 + min(0, change * 1.5))],
                'Close': [self.prices[symbol]],
                'Volume': [np.random.randint(1000000, 5000000)]
            }, index=[datetime.now()])

            self.market_data[symbol] = pd.concat([self.market_data[symbol], new_row])

        return self.prices[symbol]

    def get_market_data(self, symbol: str, interval: str = '1d', count: int = 90) -> Optional[pd.DataFrame]:
        """Get historical market data for a symbol

        Args:
            symbol: Stock symbol
            interval: Data interval (only '1d' supported in mock)
            count: Number of intervals to return

        Returns:
            DataFrame with OHLCV data or None if not available
        """
        if symbol not in self.market_data:
            # Create random data if we don't have it
            self.get_price(symbol)  # This will initialize the symbol if it's a common one

            if symbol not in self.market_data:
                logger.warning(f"Market data not found for symbol {symbol}")
                return None

        df = self.market_data[symbol].copy()
        if len(df) > count:
            df = df.iloc[-count:]

        # Calculate common technical indicators
        df['SMA_5'] = df['Close'].rolling(5).mean()
        df['SMA_10'] = df['Close'].rolling(10).mean()
        df['SMA_20'] = df['Close'].rolling(20).mean()
        df['EMA_5'] = df['Close'].ewm(span=5).mean()
        df['EMA_10'] = df['Close'].ewm(span=10).mean()
        df['EMA_20'] = df['Close'].ewm(span=20).mean()

        # Calculate RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # MACD
        df['EMA_12'] = df['Close'].ewm(span=12).mean()
        df['EMA_26'] = df['Close'].ewm(span=26).mean()
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

        # Bollinger Bands
        df['BB_Middle'] = df['SMA_20']
        df['BB_Upper'] = df['BB_Middle'] + 2 * df['Close'].rolling(20).std()
        df['BB_Lower'] = df['BB_Middle'] - 2 * df['Close'].rolling(20).std()

        # Fill NaN values
        df = df.fillna(method='bfill').fillna(method='ffill')

        return df

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions

        Returns:
            List of position dictionaries
        """
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

    def place_order(self, symbol: str, side: str, quantity: int, order_type: str = 'market',
                    limit_price: Optional[float] = None) -> Optional[str]:
        """Place an order

        Args:
            symbol: Stock symbol
            side: Order side ('buy' or 'sell')
            quantity: Order quantity
            order_type: Order type ('market' or 'limit')
            limit_price: Limit price, required for limit orders

        Returns:
            Order ID or None if order failed
        """
        self.order_id += 1
        current_price = self.get_price(symbol)

        if current_price is None:
            logger.error(f"Cannot place order - price not available for {symbol}")
            return None

        # For limit orders, check price
        if order_type.lower() == 'limit':
            if limit_price is None:
                logger.error("Limit price required for limit orders")
                return None

            # For buy orders, current price must be <= limit price
            # For sell orders, current price must be >= limit price
            if (side.lower() == 'buy' and current_price > limit_price) or \
                    (side.lower() == 'sell' and current_price < limit_price):
                logger.info(f"Limit order for {symbol} not executed, price condition not met")

                # Store as pending order
                order_id = str(self.order_id)
                self.orders[order_id] = {
                    "symbol": symbol,
                    "side": side.lower(),
                    "quantity": quantity,
                    "order_type": order_type.lower(),
                    "limit_price": limit_price,
                    "status": "pending",
                    "created_at": datetime.now().isoformat()
                }
                return order_id

        # Execute the order
        if side.lower() == "buy":
            self.positions[symbol] = {
                "entry_price": current_price,
                "quantity": quantity,
                "entry_time": datetime.now().isoformat()
            }
            logger.info(f"BUY order for {quantity} shares of {symbol} at ${current_price:.2f}")
        elif side.lower() == "sell":
            if symbol in self.positions:
                del self.positions[symbol]
                logger.info(f"SELL order for {quantity} shares of {symbol} at ${current_price:.2f}")
            else:
                logger.warning(f"Cannot sell {symbol} - no position")
                return None

        # Store completed order
        order_id = str(self.order_id)
        self.orders[order_id] = {
            "symbol": symbol,
            "side": side.lower(),
            "quantity": quantity,
            "order_type": order_type.lower(),
            "price": current_price,
            "status": "filled",
            "filled_at": datetime.now().isoformat()
        }

        return order_id