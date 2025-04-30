#!/usr/bin/env python3
"""
WebUll Trading Platform Adapter
Provides integration with WebUll API for both paper and live trading.
Includes robust error handling, retry mechanisms, and connection management.
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

# Configure logging
logger = logging.getLogger("WebUll Adapter")


class WebUllAdapter:
    """
    Adapter for integrating with WebUll trading platform API.
    Handles both paper trading and live trading modes.
    """

    # API URLs - replace with correct WebUll API endpoints
    BASE_URL = "https://userapi.webull.com/api"
    PAPER_TRADING_URL = "https://paper-api.webull.com/api"
    LOGIN_URL = "https://userapi.webull.com/api/login"
    QUOTE_URL = "https://quoteapi.webull.com/api"

    # Authentication token cache
    TOKEN_CACHE_FILE = ".webull_token_cache.json"

    def __init__(self, use_paper_trading=True, credentials=None, retry_count=3, retry_delay=2):
        """Initialize the WebUll adapter"""
        self.use_paper_trading = use_paper_trading
        self.api_url = self.PAPER_TRADING_URL if use_paper_trading else self.BASE_URL
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.session = requests.Session()
        self.authenticated = False
        self.auth_token = None
        self.token_expiry = None
        self.account_id = None
        self.credentials = credentials or {}

        # Load credentials from environment if not provided
        if not self.credentials:
            self._load_credentials_from_env()

        # Try to load cached token
        self._load_cached_token()

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

    def _load_cached_token(self):
        """Load authentication token from cache if available and not expired"""
        if os.path.exists(self.TOKEN_CACHE_FILE):
            try:
                with open(self.TOKEN_CACHE_FILE, 'r') as f:
                    cache = json.load(f)

                # Check if token is for correct mode (paper vs live)
                if cache.get('use_paper_trading') == self.use_paper_trading:
                    # Check if token is still valid
                    expiry = datetime.fromisoformat(cache.get('expiry', '2000-01-01T00:00:00'))
                    if expiry > datetime.now():
                        self.auth_token = cache.get('token')
                        self.token_expiry = expiry
                        self.account_id = cache.get('account_id')
                        self.authenticated = True
                        logger.info("Loaded valid authentication token from cache")
                        return True

            except Exception as e:
                logger.warning(f"Error loading cached token: {e}")

        return False

    def _save_token_cache(self):
        """Save authentication token to cache"""
        if self.auth_token and self.token_expiry:
            try:
                cache = {
                    'token': self.auth_token,
                    'expiry': self.token_expiry.isoformat(),
                    'account_id': self.account_id,
                    'use_paper_trading': self.use_paper_trading
                }

                with open(self.TOKEN_CACHE_FILE, 'w') as f:
                    json.dump(cache, f)

                # Secure the file with limited permissions
                os.chmod(self.TOKEN_CACHE_FILE, 0o600)

                logger.debug("Authentication token cached successfully")

            except Exception as e:
                logger.warning(f"Error caching token: {e}")

    def authenticate(self, force=False) -> bool:
        """
        Authenticate with WebUll API

        Args:
            force: Force re-authentication even if a valid token exists

        Returns:
            bool: True if authentication was successful
        """
        # If already authenticated and not forcing re-auth, return success
        if self.authenticated and not force:
            # Check if token is about to expire (within 1 hour)
            if self.token_expiry and self.token_expiry > datetime.now() + timedelta(hours=1):
                return True

        # Clear previous authentication
        self.authenticated = False
        self.auth_token = None

        # Check for required credentials
        if not all([
            self.credentials.get('username'),
            self.credentials.get('password'),
            self.credentials.get('device_id')
        ]):
            logger.error("Authentication failed: Missing required credentials")
            return False

        # Attempt authentication with retry logic
        for attempt in range(self.retry_count):
            try:
                # First step: Device ID registration
                device_data = {
                    "deviceId": self.credentials.get('device_id'),
                    "deviceName": "Trading Bot",
                    "deviceType": "Python",
                    "accountType": "N" if not self.use_paper_trading else "P"
                }

                device_response = self._make_request(
                    "post",
                    f"{self.BASE_URL}/passport/verificationCode/sendCode",
                    json=device_data,
                    auth_required=False
                )

                if not device_response.get('success', False):
                    logger.error(f"Device registration failed: {device_response}")
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue

                # Second step: Login
                login_data = {
                    "account": self.credentials.get('username'),
                    "password": self.credentials.get('password'),
                    "deviceId": self.credentials.get('device_id'),
                    "deviceName": "Trading Bot",
                    "deviceType": "Python"
                }

                login_response = self._make_request(
                    "post",
                    f"{self.LOGIN_URL}",
                    json=login_data,
                    auth_required=False
                )

                # Extract token from response
                token = login_response.get('accessToken')
                if not token:
                    logger.error(f"Login failed: {login_response}")
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue

                # Set authentication variables
                self.auth_token = token
                self.token_expiry = datetime.now() + timedelta(hours=24)  # Tokens typically valid for 24 hours

                # Get account ID
                account_response = self._make_request(
                    "get",
                    f"{self.api_url}/account/getSecAccountList",
                )

                if account_response and isinstance(account_response, list) and len(account_response) > 0:
                    self.account_id = account_response[0].get('secAccountId')

                if not self.account_id:
                    logger.error("Failed to get account ID")
                    return False

                # Success - save token and return
                self.authenticated = True
                self._save_token_cache()
                logger.info("Authentication successful")
                return True

            except Exception as e:
                logger.error(f"Authentication error (attempt {attempt + 1}/{self.retry_count}): {str(e)}")
                time.sleep(self.retry_delay * (attempt + 1))

        # All attempts failed
        logger.error("Authentication failed after all retry attempts")
        return False

    def _make_request(self, method: str, url: str, auth_required=True, **kwargs) -> Dict:
        """
        Make a request to the WebUll API with retry logic

        Args:
            method: HTTP method (get, post, etc.)
            url: API endpoint URL
            auth_required: Whether authentication is required for this request
            **kwargs: Additional arguments to pass to requests

        Returns:
            Dict: API response data
        """
        if auth_required and not self.authenticated and not self.authenticate():
            raise ValueError("Authentication required for this request")

        # Add authentication token if required
        headers = kwargs.pop('headers', {})
        if auth_required and self.auth_token:
            headers['Authorization'] = f"Bearer {self.auth_token}"

        # Set default timeout
        timeout = kwargs.pop('timeout', 30)

        # Attempt request with retry logic
        last_error = None
        for attempt in range(self.retry_count):
            try:
                response = getattr(self.session, method.lower())(
                    url,
                    headers=headers,
                    timeout=timeout,
                    **kwargs
                )

                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', self.retry_delay * (attempt + 2)))
                    logger.warning(f"Rate limited. Retrying after {retry_after} seconds")
                    time.sleep(retry_after)
                    continue

                # Check for authentication issues
                if response.status_code == 401 and auth_required:
                    logger.warning("Authentication token expired. Re-authenticating...")
                    if self.authenticate(force=True):
                        # Retry with new token
                        continue
                    else:
                        raise ValueError("Failed to re-authenticate")

                # Check for successful response
                response.raise_for_status()

                # Parse JSON response
                try:
                    return response.json()
                except ValueError:
                    # Return empty dict for empty responses
                    if not response.text:
                        return {}
                    # Return text for non-JSON responses
                    return {"text": response.text}

            except requests.exceptions.RequestException as e:
                last_error = e
                logger.warning(f"API request failed (attempt {attempt + 1}/{self.retry_count}): {str(e)}")
                time.sleep(self.retry_delay * (attempt + 1))

        # All attempts failed
        error_msg = f"API request failed after {self.retry_count} attempts"
        if last_error:
            error_msg += f": {str(last_error)}"

        raise ValueError(error_msg)

    def get_price(self, symbol: str) -> Optional[float]:
        """
        Get the current price for a symbol

        Args:
            symbol: Stock symbol (e.g., 'AAPL')

        Returns:
            float: Current price or None if not available
        """
        try:
            response = self._make_request(
                "get",
                f"{self.QUOTE_URL}/quote/tickerRealTimes/v5/{symbol}",
                auth_required=True
            )

            if response and response.get('close'):
                return float(response.get('close'))

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
            if not self.account_id:
                logger.error("No account ID available")
                return {}

            response = self._make_request(
                "get",
                f"{self.api_url}/account/getAccount/{self.account_id}",
                auth_required=True
            )

            return response or {}

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
            if not self.account_id:
                logger.error("No account ID available")
                return []

            response = self._make_request(
                "get",
                f"{self.api_url}/account/getPositions/{self.account_id}",
                auth_required=True
            )

            if response and isinstance(response, list):
                return response

            return []

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
            # Validate required parameters
            if side not in ["BUY", "SELL"]:
                raise ValueError(f"Invalid order side: {side}")

            if order_type not in ["MKT", "LMT", "STP", "STP_LMT"]:
                raise ValueError(f"Invalid order type: {order_type}")

            if order_type in ["LMT", "STP_LMT"] and limit_price is None:
                raise ValueError("Limit price required for LMT and STP_LMT orders")

            if order_type in ["STP", "STP_LMT"] and stop_price is None:
                raise ValueError("Stop price required for STP and STP_LMT orders")

            if time_in_force not in ["GTC", "DAY", "IOC"]:
                raise ValueError(f"Invalid time in force: {time_in_force}")

            if not self.account_id:
                raise ValueError("No account ID available")

            # Get ticker ID
            ticker_info = self._make_request(
                "get",
                f"{self.QUOTE_URL}/search/tickers5",
                params={"keys": symbol, "queryNumber": 1},
                auth_required=True
            )

            if not ticker_info or not isinstance(ticker_info, list) or len(ticker_info) == 0:
                raise ValueError(f"Symbol not found: {symbol}")

            ticker_id = ticker_info[0].get('tickerId')
            if not ticker_id:
                raise ValueError(f"Ticker ID not found for symbol: {symbol}")

            # Prepare order parameters
            order_params = {
                "secAccountId": self.account_id,
                "tickerId": ticker_id,
                "action": side,
                "orderType": order_type,
                "quantity": quantity,
                "timeInForce": time_in_force,
                "outsideRegularTradingHour": True,  # Allow extended hours trading
                "comboType": "NORMAL"
            }

            # Add limit price if provided
            if limit_price is not None:
                order_params["lmtPrice"] = limit_price

            # Add stop price if provided
            if stop_price is not None:
                order_params["stopPrice"] = stop_price

            # Add trading PIN for live trading
            if not self.use_paper_trading and self.credentials.get('trading_pin'):
                order_params["pin"] = self.credentials.get('trading_pin')

            # Place order
            response = self._make_request(
                "post",
                f"{self.api_url}/order/place",
                json=order_params,
                auth_required=True
            )

            if response and response.get('orderId'):
                logger.info(f"Order placed successfully: {response.get('orderId')}")
                return response

            logger.error(f"Failed to place order: {response}")
            return response or {}

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
            if not self.account_id:
                logger.error("No account ID available")
                return False

            response = self._make_request(
                "post",
                f"{self.api_url}/order/cancelStockOrder/{self.account_id}/{order_id}",
                auth_required=True
            )

            success = response and response.get('success', False)
            if success:
                logger.info(f"Order {order_id} cancelled successfully")
            else:
                logger.error(f"Failed to cancel order {order_id}: {response}")

            return success

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
            if not self.account_id:
                logger.error("No account ID available")
                return {}

            response = self._make_request(
                "get",
                f"{self.api_url}/order/{order_id}",
                auth_required=True
            )

            return response or {}

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
            if not self.account_id:
                logger.error("No account ID available")
                return []

            # Default to last 7 days if no time range specified
            if end_time is None:
                end_time = datetime.now()

            if start_time is None:
                start_time = end_time - timedelta(days=7)

            # Convert time to string format
            start_str = start_time.strftime("%Y-%m-%d")
            end_str = end_time.strftime("%Y-%m-%d")

            params = {
                "secAccountId": self.account_id,
                "startTime": start_str,
                "endTime": end_str
            }

            # Add status filter if not 'all'
            if status != "all":
                status_map = {
                    "open": "Working",
                    "closed": "Filled",
                    "cancelled": "Cancelled"
                }
                if status in status_map:
                    params["status"] = status_map[status]

            response = self._make_request(
                "get",
                f"{self.api_url}/order/list",
                params=params,
                auth_required=True
            )

            if response and isinstance(response, list):
                return response

            return []

        except Exception as e:
            logger.error(f"Error getting order history: {str(e)}")
            return []

    def get_market_hours(self) -> Dict:
        """
        Get market trading hours

        Returns:
            Dict: Market hours information
        """
        try:
            response = self._make_request(
                "get",
                f"{self.QUOTE_URL}/quote/query/getTradeDay",
                auth_required=True
            )

            return response or {}

        except Exception as e:
            logger.error(f"Error getting market hours: {str(e)}")
            return {}

    def is_market_open(self) -> bool:
        """
        Check if the market is currently open

        Returns:
            bool: True if market is open
        """
        try:
            market_hours = self.get_market_hours()

            # Extract market status
            is_open = market_hours.get('isOpen', False)

            # Also check if we're within regular market hours
            current_time = datetime.now().time()
            market_open_time = datetime.strptime("09:30", "%H:%M").time()
            market_close_time = datetime.strptime("16:00", "%H:%M").time()

            within_hours = market_open_time <= current_time <= market_close_time

            # Check if today is a trading day
            is_trading_day = market_hours.get('isTradingDay', False)

            return is_open and within_hours and is_trading_day

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
            if not self.account_id:
                logger.error("No account ID available")
                return {}

            response = self._make_request(
                "get",
                f"{self.api_url}/account/getBalance/{self.account_id}",
                auth_required=True
            )

            # Extract relevant balance information
            if response:
                return {
                    "buying_power": response.get('buyingPower', 0),
                    "cash_balance": response.get('cashBalance', 0),
                    "equity_value": response.get('equityValue', 0),
                    "total_value": response.get('totalValue', 0),
                    "unrealized_profit_loss": response.get('unrealizedProfitLoss', 0),
                    "unrealized_profit_loss_rate": response.get('unrealizedProfitLossRate', 0)
                }

            return {}

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
            # Map interval to WebUll format
            interval_map = {
                "1m": "m1",
                "5m": "m5",
                "15m": "m15",
                "30m": "m30",
                "1h": "h1",
                "1d": "d1",
                "1w": "w1",
                "1mo": "mo1"
            }

            web_interval = interval_map.get(interval)
            if not web_interval:
                raise ValueError(f"Invalid interval: {interval}")

            # Get ticker ID first
            ticker_info = self._make_request(
                "get",
                f"{self.QUOTE_URL}/search/tickers5",
                params={"keys": symbol, "queryNumber": 1},
                auth_required=True
            )

            if not ticker_info or not isinstance(ticker_info, list) or len(ticker_info) == 0:
                raise ValueError(f"Symbol not found: {symbol}")

            ticker_id = ticker_info[0].get('tickerId')
            if not ticker_id:
                raise ValueError(f"Ticker ID not found for symbol: {symbol}")

            # Get historical data
            params = {
                "tickerId": ticker_id,
                "type": web_interval,
                "count": count
            }

            response = self._make_request(
                "get",
                f"{self.QUOTE_URL}/quote/charts/query",
                params=params,
                auth_required=True
            )

            if not response or not response.get('data'):
                return pd.DataFrame()

            # Convert to DataFrame
            data = response.get('data', [])
            df = pd.DataFrame(data)

            # Rename columns to standard format
            column_map = {
                "t": "timestamp",
                "o": "open",
                "h": "high",
                "l": "low",
                "c": "close",
                "v": "volume"
            }

            df = df.rename(columns=column_map)

            # Convert timestamp to datetime
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df.set_index("timestamp", inplace=True)

            # Convert price columns to float
            for col in ["open", "high", "low", "close"]:
                if col in df.columns:
                    df[col] = df[col].astype(float)

            # Convert volume to integer if present
            if "volume" in df.columns:
                df["volume"] = df["volume"].astype(int)

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
                price = self.get_price("AAPL")
                if price is not None:
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
            self.session.close()
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

            # Get market hours
            is_open = adapter.is_market_open()
            print(f"Market is {'open' if is_open else 'closed'}")

            # Get account balance
            balance = adapter.get_account_balance()
            print(f"Account Balance: {balance}")

            # Get positions
            positions = adapter.get_positions()
            print(f"Current Positions: {len(positions)}")

            # Get historical data for a symbol
            data = adapter.get_historical_data("AAPL", interval="1d", count=10)
            print(f"AAPL Historical Data:\n{data.head()}")

        else:
            print("Authentication failed")

    finally:
        # Close adapter
        adapter.close()
