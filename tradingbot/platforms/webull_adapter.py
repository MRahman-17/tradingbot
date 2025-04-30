import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional
import os
from platforms.platform_base import PlatformAdapter

logger = logging.getLogger(__name__)


class WebullAdapter(PlatformAdapter):
    """Adapter for WebUll trading platform"""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize WebUll adapter with configuration

        Args:
            config: Platform configuration
        """
        super().__init__(config)
        self.name = "webull"
        self.authenticated = False
        self.client = None

        # Try to import webull package
        try:
            from webull import webull
            self.webull_available = True
            self.webull_client = webull()
            logger.info("WebUll package imported successfully")
        except ImportError:
            self.webull_available = False
            logger.error("WebUll package not available, please install with: pip install webull-api")

    def login(self) -> bool:
        """Authenticate with the WebUll platform

        Returns:
            True if authentication succeeded, False otherwise
        """
        if not self.webull_available:
            logger.error("WebUll package not available")
            return False

        try:
            # Get credentials from environment variables
            username = os.environ.get("WEBULL_USERNAME")
            password = os.environ.get("WEBULL_PASSWORD")
            device_id = os.environ.get("WEBULL_DEVICE_ID")
            trade_pin = os.environ.get("WEBULL_TRADE_PIN")

            if not username or not password:
                logger.error("WebUll credentials not found in environment variables")
                return False

            # Login to WebUll
            self.webull_client.login(username, password, device_id)

            # Set trade PIN if available and using paper trading
            if trade_pin and self.config.get("use_paper_trading", True):
                self.webull_client.get_trade_token(trade_pin)

            # Use paper trading if configured
            if self.config.get("use_paper_trading", True):
                self.webull_client.use_paper_account()
                logger.info("Using WebUll paper trading account")

            self.authenticated = True
            logger.info("WebUll login successful")
            return True
        except Exception as e:
            logger.error(f"WebUll login failed: {e}")
            return False

    def logout(self) -> bool:
        """Logout from the WebUll platform

        Returns:
            True if logout succeeded, False otherwise
        """
        if not self.webull_available or not self.authenticated:
            return False

        try:
            self.webull_client.logout()
            self.authenticated = False
            logger.info("WebUll logout successful")
            return True
        except Exception as e:
            logger.error(f"WebUll logout failed: {e}")
            return False

    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol

        Args:
            symbol: Stock symbol

        Returns:
            Current price or None if not available
        """
        if not self.webull_available or not self.authenticated:
            logger.error("WebUll not available or not authenticated")
            return None

        try:
            quote = self.webull_client.get_quote(symbol)
            if quote and 'close' in quote:
                return float(quote['close'])
            else:
                logger.warning(f"Price not found for symbol {symbol}")
                return None
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None

    def get_market_data(self, symbol: str, interval: str = '1d', count: int = 90) -> Optional[pd.DataFrame]:
        """Get historical market data for a symbol

        Args:
            symbol: Stock symbol
            interval: Data interval ('1m', '5m', '15m', '30m', '1h', '1d', '1w')
            count: Number of intervals to return

        Returns:
            DataFrame with OHLCV data or None if not available
        """
        if not self.webull_available or not self.authenticated:
            logger.error("WebUll not available or not authenticated")
            return None

        try:
            # Convert interval to WebUll format
            webull_interval = {
                '1m': 'm1',
                '5m': 'm5',
                '15m': 'm15',
                '30m': 'm30',
                '1h': 'h1',
                '1d': 'd1',
                '1w': 'w1'
            }.get(interval, 'd1')

            # Get historical data
            bars = self.webull_client.get_bars(symbol, webull_interval, count)

            if not bars:
                logger.warning(f"No historical data found for {symbol}")
                return None

            # Convert to pandas DataFrame
            df = pd.DataFrame(bars)

            # Rename columns to match our standard format
            df.rename(columns={
                'time': 'Date',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }, inplace=True)

            # Convert timestamp to datetime and set as index
            df['Date'] = pd.to_datetime(df['Date'], unit='ms')
            df.set_index('Date', inplace=True)

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
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return None

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions

        Returns:
            List of position dictionaries
        """
        if not self.webull_available or not self.authenticated:
            logger.error("WebUll not available or not authenticated")
            return []

        try:
            positions = []

            # Get positions from WebUll
            raw_positions = self.webull_client.get_positions()

            if not raw_positions:
                return []

            for pos in raw_positions:
                symbol = pos.get('ticker', {}).get('symbol')
                if not symbol:
                    continue

                quantity = float(pos.get('position', 0))
                entry_price = float(pos.get('costPrice', 0))
                current_price = float(pos.get('lastPrice', 0))

                # Calculate P&L
                unrealized_pl = (current_price - entry_price) * quantity
                unrealized_pl_pct = (current_price / entry_price - 1) * 100 if entry_price > 0 else 0

                positions.append({
                    "symbol": symbol,
                    "quantity": quantity,
                    "entry_price": entry_price,
                    "current_price": current_price,
                    "unrealized_pl": unrealized_pl,
                    "unrealized_pl_percent": unrealized_pl_pct
                })

            return positions
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

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
        if not self.webull_available or not self.authenticated:
            logger.error("WebUll not available or not authenticated")
            return None

        try:
            # Get ticker ID
            ticker_info = self.webull_client.get_ticker(symbol)
            if not ticker_info:
                logger.error(f"Symbol {symbol} not found")
                return None

            ticker_id = ticker_info.get('tickerId')
            if not ticker_id:
                logger.error(f"Ticker ID not found for {symbol}")
                return None

            # Place order
            if order_type.lower() == 'market':
                if side.lower() == 'buy':
                    order_id = self.webull_client.place_order(
                        stock=ticker_id,
                        action='BUY',
                        quant=quantity,
                        orderType='MKT'
                    )
                else:  # sell
                    order_id = self.webull_client.place_order(
                        stock=ticker_id,
                        action='SELL',
                        quant=quantity,
                        orderType='MKT'
                    )
            elif order_type.lower() == 'limit':
                if not limit_price:
                    logger.error("Limit price required for limit orders")
                    return None

                if side.lower() == 'buy':
                    order_id = self.webull_client.place_order(
                        stock=ticker_id,
                        action='BUY',
                        quant=quantity,
                        orderType='LMT',
                        price=limit_price
                    )
                else:  # sell
                    order_id = self.webull_client.place_order(
                        stock=ticker_id,
                        action='SELL',
                        quant=quantity,
                        orderType='LMT',
                        price=limit_price
                    )
            else:
                logger.error(f"Unsupported order type: {order_type}")
                return None

            if order_id:
                logger.info(f"{side.upper()} order placed for {quantity} shares of {symbol}")
                return str(order_id)
            else:
                logger.error(f"Failed to place order for {symbol}")
                return None
        except Exception as e:
            logger.error(f"Error placing order for {symbol}: {e}")
            return None

    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an order

        Args:
            order_id: Order ID

        Returns:
            Order status dictionary or None if not found
        """
        if not self.webull_available or not self.authenticated:
            logger.error("WebUll not available or not authenticated")
            return None

        try:
            # Get order details
            order = self.webull_client.get_order(order_id)
            if not order:
                logger.warning(f"Order {order_id} not found")
                return None

            # Convert to our standard format
            status_map = {
                'PendingNew': 'pending',
                'New': 'pending',
                'Filled': 'filled',
                'PartiallyFilled': 'partially_filled',
                'Canceled': 'cancelled',
                'Rejected': 'rejected'
            }

            return {
                "order_id": order_id,
                "symbol": order.get('ticker', {}).get('symbol', ''),
                "side": order.get('action', '').lower(),
                "quantity": float(order.get('quantity', 0)),
                "filled_quantity": float(order.get('filledQuantity', 0)),
                "order_type": order.get('orderType', '').lower(),
                "limit_price": float(order.get('lmtPrice', 0)) if order.get('lmtPrice') else None,
                "status": status_map.get(order.get('status'), 'unknown'),
                "created_at": order.get('createTime'),
                "updated_at": order.get('updateTime')
            }
        except Exception as e:
            logger.error(f"Error getting order status for {order_id}: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order

        Args:
            order_id: Order ID

        Returns:
            True if cancellation succeeded, False otherwise
        """
        if not self.webull_available or not self.authenticated:
            logger.error("WebUll not available or not authenticated")
            return False

        try:
            result = self.webull_client.cancel_order(order_id)
            if result == order_id:
                logger.info(f"Order {order_id} cancelled")
                return True
            else:
                logger.warning(f"Failed to cancel order {order_id}")
                return False
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False