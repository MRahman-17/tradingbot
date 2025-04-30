#!/usr/bin/env python3
"""
WebUll Trading Platform Adapter using tedchou12/webull package
Provides integration with WebUll API for both paper and live trading.
"""
import os
import time
import json
import logging
import requests
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import uuid
import hashlib

# Configure logging
logger = logging.getLogger("WebUll Adapter")

try:
    # Import the webull package
    from webull import webull
    from webull import paper_webull

    WEBULL_PACKAGE_AVAILABLE = True
except ImportError:
    logger.error("Could not import webull package. Please install with: pip install webull")
    WEBULL_PACKAGE_AVAILABLE = False


class WebUllAdapter:
    """
    Adapter for integrating with WebUll trading platform API using tedchou12/webull package.
    Handles both paper trading and live trading modes.
    """

    def __init__(self, use_paper_trading=True, credentials=None, retry_count=3, retry_delay=2):
        """Initialize the WebUll adapter"""
        self.use_paper_trading = use_paper_trading
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.authenticated = False
        self.credentials = credentials or {}
        self.wb = None

        # Load credentials from environment if not provided
        if not self.credentials:
            self._load_credentials_from_env()

        # Initialize the webull client
        self._init_webull_client()

        logger.info(f"WebUll Adapter initialized in {'paper' if use_paper_trading else 'live'} trading mode")

    def _load_credentials_from_env(self):
        """Load WebUll credentials from environment variables"""
        self.credentials = {
            "username": os.environ.get("WEBULL_USERNAME", ""),
            "password": os.environ.get("WEBULL_PASSWORD", ""),
            "device_id": os.environ.get("WEBULL_DEVICE_ID", ""),
            "trading_pin": os.environ.get("WEBULL_TRADING_PIN", ""),
        }

        # Generate a device ID if not provided
        if not self.credentials["device_id"]:
            import uuid
            import hashlib
            # Create a deterministic device ID based on username
            if self.credentials["username"]:
                device_seed = f"trading_bot_{self.credentials['username']}"
                device_hash = hashlib.md5(device_seed.encode()).hexdigest()
                self.credentials["device_id"] = f"TradingBot-{device_hash[:12]}"
                logger.info(f"Generated device ID for WebUll: {self.credentials['device_id']}")
            else:
                # Completely random device ID if no username
                self.credentials["device_id"] = f"TradingBot-{uuid.uuid4().hex[:12]}"
                logger.info(f"Generated random device ID for WebUll: {self.credentials['device_id']}")

        # Warn if credentials are missing (excluding device_id since we generate it)
        missing = [k for k, v in self.credentials.items() if not v and k != "device_id"]
        if missing:
            logger.warning(f"Missing WebUll credentials: {', '.join(missing)}")

    def _init_webull_client(self):
        """Initialize the webull client with the appropriate class"""
        if not WEBULL_PACKAGE_AVAILABLE:
            logger.error("Cannot initialize webull client: package not available")
            return False

        try:
            # Choose the appropriate client type
            if self.use_paper_trading:
                self.wb = paper_webull()
            else:
                self.wb = webull()

            # Set the device ID if provided
            if self.credentials.get("device_id"):
                self.wb.did = self.credentials["device_id"]

            return True
        except Exception as e:
            logger.error(f"Error initializing webull client: {str(e)}")
            return False

    def authenticate(self, force=False) -> bool:
        """
        Authenticate with WebUll API

        Args:
            force: Force re-authentication even if already authenticated

        Returns:
            bool: True if authentication was successful
        """
        if self.authenticated and not force:
            return True

        if not self.wb:
            logger.error("WebUll client not initialized")
            return False

        # Check for required credentials
        if not self.credentials.get('username') or not self.credentials.get('password'):
            logger.error("Authentication failed: Missing username or password")
            return False

        # Attempt authentication with retry logic
        for attempt in range(self.retry_count):
            try:
                # Login to WebUll
                login_success = self.wb.login(
                    username=self.credentials['username'],
                    password=self.credentials['password']
                )

                if not login_success:
                    logger.error("Authentication failed: Login returned failure")
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue

                # Set trading PIN if available
                if self.credentials.get('trading_pin'):
                    try:
                        self.wb.get_trade_token(self.credentials['trading_pin'])
                    except Exception as e:
                        logger.warning(f"Could not set trade token: {str(e)}")

                # Success
                self.authenticated = True
                logger.info("Authentication successful")
                return True

            except Exception as e:
                logger.error(f"Authentication error (attempt {attempt + 1}/{self.retry_count}): {str(e)}")
                time.sleep(self.retry_delay * (attempt + 1))

        # All attempts failed
        logger.error("Authentication failed after all retry attempts")
        return False

    def get_price(self, symbol: str) -> Optional[float]:
        """
        Get the current price for a symbol

        Args:
            symbol: Stock symbol (e.g., 'AAPL')

        Returns:
            float: Current price or None if not available
        """
        try:
            if not self.wb:
                logger.error("WebUll client not initialized")
                return None

            # Ensure authenticated
            if not self.authenticated and not self.authenticate():
                logger.error("Cannot get price: Not authenticated")
                return None

            # Get quote data
            quote = self.wb.get_quote(symbol)

            if quote and 'close' in quote:
                return float(quote['close'])

            return None

        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {str(e)}")
            return None

    def get_account_info(self) -> Dict:
        """
        Get account information

        Returns:
            Dict: Account information
        """
        try:
            if not self.wb:
                logger.error("WebUll client not initialized")
                return {}

            # Ensure authenticated
            if not self.authenticated and not self.authenticate():
                logger.error("Cannot get account info: Not authenticated")
                return {}

            # Get account info
            account_info = self.wb.get_account()
            return account_info or {}

        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return {}

    def get_positions(self) -> List[Dict]:
        """
        Get current positions

        Returns:
            List[Dict]: List of current positions
        """
        try:
            if not self.wb:
                logger.error("WebUll client not initialized")
                return []

            # Ensure authenticated
            if not self.authenticated and not self.authenticate():
                logger.error("Cannot get positions: Not authenticated")
                return []

            # Get positions
            positions = self.wb.get_positions()
            return positions if isinstance(positions, list) else []

        except Exception as e:
            logger.error(f"Error getting positions: {str(e)}")
            return []

    def place_order(self, symbol: str, side: str, quantity: int, order_type: str = "MKT",
                    limit_price: Optional[float] = None, stop_price: Optional[float] = None,
                    time_in_force: str = "GTC") -> Dict:
        """
        Place a new order

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            side: Order side ('BUY' or 'SELL')
            quantity: Number of shares
            order_type: Order type ('MKT', 'LMT', 'STP', 'STP_LMT')
            limit_price: Limit price (required for LMT and STP_LMT orders)
            stop_price: Stop price (required for STP and STP_LMT orders)
            time_in_force: Time in force ('GTC', 'DAY', 'IOC')

        Returns:
            Dict: Order response data
        """
        try:
            if not self.wb:
                logger.error("WebUll client not initialized")
                return {"error": "WebUll client not initialized"}

            # Ensure authenticated
            if not self.authenticated and not self.authenticate():
                logger.error("Cannot place order: Not authenticated")
                return {"error": "Not authenticated"}

            # Validate parameters
            if not symbol:
                raise ValueError("Stock symbol is required")

            if quantity <= 0:
                raise ValueError("Quantity must be greater than 0")

            # Map parameters to webull package format
            action = side.lower()
            price = limit_price if order_type in ["LMT", "STP_LMT"] else None

            # Place the order using the appropriate method
            if action == "buy":
                order_id = self.wb.place_order(
                    stock=symbol,
                    price=price,
                    qty=quantity,
                    order_type=order_type,
                    outside_regular_trading_hour=True,
                    time_in_force=time_in_force
                )
            elif action == "sell":
                order_id = self.wb.place_order(
                    stock=symbol,
                    price=price,
                    qty=quantity,
                    order_type=order_type,
                    action="SELL",
                    outside_regular_trading_hour=True,
                    time_in_force=time_in_force
                )
            else:
                raise ValueError(f"Invalid order side: {side}")

            if order_id:
                logger.info(f"Order placed successfully: {order_id}")
                return {"orderId": order_id}
            else:
                logger.error("Failed to place order: No order ID returned")
                return {"error": "Failed to place order"}

        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            return {"error": str(e)}

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order

        Args:
            order_id: Order ID to cancel

        Returns:
            bool: True if cancellation was successful
        """
        try:
            if not self.wb:
                logger.error("WebUll client not initialized")
                return False

            # Ensure authenticated
            if not self.authenticated and not self.authenticate():
                logger.error("Cannot cancel order: Not authenticated")
                return False

            # Cancel the order
            result = self.wb.cancel_order(order_id)

            if result:
                logger.info(f"Order {order_id} cancelled successfully")
                return True
            else:
                logger.error(f"Failed to cancel order {order_id}")
                return False

        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {str(e)}")
            return False

    def get_order_status(self, order_id: str) -> Dict:
        """
        Get the status of an order

        Args:
            order_id: Order ID to check

        Returns:
            Dict: Order status information
        """
        try:
            if not self.wb:
                logger.error("WebUll client not initialized")
                return {}

            # Ensure authenticated
            if not self.authenticated and not self.authenticate():
                logger.error("Cannot get order status: Not authenticated")
                return {}

            # Get all orders and find the specific one
            orders = self.wb.get_current_orders()

            if not orders:
                return {}

            for order in orders:
                if order.get('orderId') == order_id:
                    return order

            return {}

        except Exception as e:
            logger.error(f"Error getting order status for {order_id}: {str(e)}")
            return {}

    def get_order_history(self, status: str = "all", start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None) -> List[Dict]:
        """
        Get order history

        Args:
            status: Filter by status ('all', 'open', 'closed', 'cancelled')
            start_time: Start time for filtering
            end_time: End time for filtering

        Returns:
            List[Dict]: List of orders
        """
        try:
            if not self.wb:
                logger.error("WebUll client not initialized")
                return []

            # Ensure authenticated
            if not self.authenticated and not self.authenticate():
                logger.error("Cannot get order history: Not authenticated")
                return []

            # Get all orders using the built-in function
            if status == "all":
                orders = self.wb.get_history_orders()
            elif status == "open":
                orders = self.wb.get_current_orders()
            else:
                # Get all orders and filter manually
                orders = self.wb.get_history_orders()

                # Filter based on status
                if status == "closed":
                    orders = [o for o in orders if o.get('statusCode') == 'Filled']
                elif status == "cancelled":
                    orders = [o for o in orders if o.get('statusCode') == 'Cancelled']

            # Filter by date if provided
            if start_time or end_time:
                filtered_orders = []
                for order in orders:
                    order_time = None
                    if 'createTime' in order:
                        try:
                            order_time = datetime.fromisoformat(order['createTime'].replace('Z', '+00:00'))
                        except (ValueError, TypeError):
                            continue

                    if order_time:
                        if start_time and order_time < start_time:
                            continue
                        if end_time and order_time > end_time:
                            continue
                        filtered_orders.append(order)
                return filtered_orders

            return orders or []

        except Exception as e:
            logger.error(f"Error getting order history: {str(e)}")
            return []

    def is_market_open(self) -> bool:
        """
        Check if the market is currently open

        Returns:
            bool: True if market is open
        """
        try:
            if not self.wb:
                logger.error("WebUll client not initialized")
                return False

            # Use the webull function to check if market is open
            is_open = self.wb.is_market_open()
            return bool(is_open)

        except Exception as e:
            logger.error(f"Error checking if market is open: {str(e)}")
            return False

    def get_account_balance(self) -> Dict:
        """
        Get account balance information

        Returns:
            Dict: Account balance details
        """
        try:
            if not self.wb:
                logger.error("WebUll client not initialized")
                return {}

            # Ensure authenticated
            if not self.authenticated and not self.authenticate():
                logger.error("Cannot get account balance: Not authenticated")
                return {}

            # Get account info which includes balance
            account = self.wb.get_account()

            if not account:
                return {}

            # Extract relevant balance information
            balance = {
                "buying_power": account.get('buyingPower', 0),
                "cash_balance": account.get('cashBalance', 0),
                "equity_value": account.get('equity', 0),
                "total_value": account.get('netLiquidation', 0)
            }

            return balance

        except Exception as e:
            logger.error(f"Error getting account balance: {str(e)}")
            return {}

    def get_historical_data(self, symbol: str, interval: str = "1d",
                            count: int = 30) -> pd.DataFrame:
        """
        Get historical price data

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            interval: Data interval ('1m', '5m', '15m', '30m', '1h', '1d', '1w', '1mo')
            count: Number of bars to retrieve

        Returns:
            pd.DataFrame: Historical price data
        """
        try:
            if not self.wb:
                logger.error("WebUll client not initialized")
                return pd.DataFrame()

            # Map interval to format expected by webull package
            interval_map = {
                "1m": "m1",
                "5m": "m5",
                "15m": "m15",
                "30m": "m30",
                "1h": "h1",
                "1d": "d1",
                "1w": "w1",
                "1mo": "m1"
            }

            wb_interval = interval_map.get(interval, "d1")

            # Get historical data
            bars = self.wb.get_bars(symbol, interval=wb_interval, count=count)

            if bars is None or len(bars) == 0:
                return pd.DataFrame()

            # Convert to dataframe
            df = pd.DataFrame(bars)

            # Rename columns to standard format
            if 'time' in df.columns:
                df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
                df.set_index('timestamp', inplace=True)

            return df

        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            return pd.DataFrame()

    def health_check(self) -> Dict:
        """
        Perform a health check on the WebUll API connection

        Returns:
            Dict: Health check results
        """
        results = {
            "status": "Unavailable",
            "authenticated": False,
            "account_accessible": False,
            "market_data_accessible": False,
            "errors": []
        }

        if not WEBULL_PACKAGE_AVAILABLE:
            results["errors"].append("WebUll package not installed")
            return results

        if not self.wb:
            results["errors"].append("WebUll client not initialized")
            return results

        try:
            # Check authentication
            if not self.authenticated:
                auth_result = self.authenticate()
                results["authenticated"] = auth_result
                if not auth_result:
                    results["errors"].append("Authentication failed")
                    return results
            else:
                results["authenticated"] = True

            # Check account access
            account_info = self.get_account_info()
            if account_info:
                results["account_accessible"] = True
            else:
                results["errors"].append("Account information not accessible")

            # Check market data
            try:
                quote = self.wb.get_quote("AAPL")
                if quote:
                    results["market_data_accessible"] = True
                else:
                    results["errors"].append("Market data not accessible")
            except Exception as e:
                results["errors"].append(f"Market data error: {str(e)}")

            # Overall status
            if results["authenticated"] and results["account_accessible"] and results["market_data_accessible"]:
                results["status"] = "OK"
            elif results["authenticated"]:
                results["status"] = "Partial"
            else:
                results["status"] = "Error"

            return results

        except Exception as e:
            results["errors"].append(f"Health check error: {str(e)}")
            return results

    def close(self):
        """Close the adapter and clean up resources"""
        try:
            # No explicit close method needed for webull package
            self.authenticated = False
            self.wb = None
            logger.info("WebUll adapter closed")
        except Exception as e:
            logger.error(f"Error closing adapter: {str(e)}")


# Helper factory function to create adapter instance
def create_webull_adapter(use_paper_trading=None):
    """
    Create a WebUll adapter instance with settings from environment variables

    Args:
        use_paper_trading: Override environment setting for paper trading

    Returns:
        WebUllAdapter: Configured adapter instance
    """
    # Determine paper trading mode from environment if not specified
    if use_paper_trading is None:
        trading_mode = os.environ.get("TRADING_MODE", "paper").lower()
        use_paper_trading = trading_mode in ["paper", "test", "sandbox"]

    # Create and return adapter
    adapter = WebUllAdapter(use_paper_trading=use_paper_trading)

    return adapter


# Example usage
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create adapter
    adapter = create_webull_adapter()

    try:
        # Authenticate
        if adapter.authenticate():
            print("Authentication successful")

            # Check health
            health = adapter.health_check()
            print(f"API Health: {health['status']}")

            # Get account balance
            balance = adapter.get_account_balance()
            print(f"Account Balance: {balance}")

            # Get positions
            positions = adapter.get_positions()
            print(f"Current Positions: {len(positions)}")

        else:
            print("Authentication failed")

    finally:
        # Close adapter
        adapter.close()
