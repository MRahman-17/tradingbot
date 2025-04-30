import abc
import logging
from typing import Dict, List, Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class PlatformAdapter(abc.ABC):
    """Base class for trading platform adapters"""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize platform adapter with configuration

        Args:
            config: Platform configuration
        """
        self.config = config
        self.name = "base"
        self.authenticated = False

    @abc.abstractmethod
    def login(self) -> bool:
        """Authenticate with the trading platform

        Returns:
            True if authentication succeeded, False otherwise
        """
        pass

    @abc.abstractmethod
    def logout(self) -> bool:
        """Logout from the trading platform

        Returns:
            True if logout succeeded, False otherwise
        """
        pass

    @abc.abstractmethod
    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol

        Args:
            symbol: Stock symbol

        Returns:
            Current price or None if not available
        """
        pass

    @abc.abstractmethod
    def get_market_data(self, symbol: str, interval: str = '1d', count: int = 90) -> Optional[pd.DataFrame]:
        """Get historical market data for a symbol

        Args:
            symbol: Stock symbol
            interval: Data interval ('1m', '5m', '15m', '30m', '1h', '1d', '1w')
            count: Number of intervals to return

        Returns:
            DataFrame with OHLCV data or None if not available
        """
        pass

    @abc.abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions

        Returns:
            List of position dictionaries
        """
        pass

    @abc.abstractmethod
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

    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an order

        Args:
            order_id: Order ID

        Returns:
            Order status dictionary or None if not found
        """
        if order_id in self.orders:
            # Check if pending limit orders can be filled
            order = self.orders[order_id]
            if order["status"] == "pending" and order["order_type"] == "limit":
                current_price = self.get_price(order["symbol"])

                # Check if limit order can be filled
                if (order["side"] == "buy" and current_price <= order["limit_price"]) or \
                        (order["side"] == "sell" and current_price >= order["limit_price"]):
                    # Fill the order
                    if order["side"] == "buy":
                        self.positions[order["symbol"]] = {
                            "entry_price": order["limit_price"],
                            "quantity": order["quantity"],
                            "entry_time": datetime.now().isoformat()
                        }
                    elif order["side"] == "sell" and order["symbol"] in self.positions:
                        del self.positions[order["symbol"]]

                    # Update order status
                    self.orders[order_id]["status"] = "filled"
                    self.orders[order_id]["filled_at"] = datetime.now().isoformat()
                    self.orders[order_id]["price"] = order["limit_price"]

                    logger.info(f"Limit order {order_id} for {order['symbol']} filled at {order['limit_price']}")

            return self.orders[order_id]
        else:
            logger.warning(f"Order {order_id} not found")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order

        Args:
            order_id: Order ID

        Returns:
            True if cancellation succeeded, False otherwise
        """
        if order_id in self.orders:
            order = self.orders[order_id]
            if order["status"] == "pending":
                self.orders[order_id]["status"] = "cancelled"
                self.orders[order_id]["cancelled_at"] = datetime.now().isoformat()
                logger.info(f"Order {order_id} cancelled")
                return True
            else:
                logger.warning(f"Cannot cancel order {order_id}, status: {order['status']}")
                return False
        else:
            logger.warning(f"Order {order_id} not found")
            return False
