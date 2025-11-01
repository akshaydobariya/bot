"""
Enhanced Delta Exchange API Client for India
Production-ready implementation with comprehensive error handling, rate limiting, and monitoring
"""

import time
import hmac
import hashlib
import json
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

import requests
import websocket
import pandas as pd
from loguru import logger
from ratelimit import limits, sleep_and_retry
import backoff

from src.config import settings


class OrderSide(str, Enum):
    """Order side enumeration"""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type enumeration"""
    LIMIT = "limit_order"
    MARKET = "market_order"
    STOP_LOSS = "stop_loss_order"
    TAKE_PROFIT = "take_profit_order"
    STOP_LOSS_LIMIT = "stop_loss_limit_order"
    TAKE_PROFIT_LIMIT = "take_profit_limit_order"


class TimeInForce(str, Enum):
    """Time in force enumeration"""
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill


@dataclass
class OrderRequest:
    """Order request data structure"""
    product_id: int
    side: OrderSide
    size: str
    order_type: OrderType = OrderType.LIMIT
    limit_price: Optional[str] = None
    stop_price: Optional[str] = None
    time_in_force: TimeInForce = TimeInForce.GTC
    post_only: bool = False
    reduce_only: bool = False
    client_order_id: Optional[str] = None


@dataclass
class Position:
    """Position data structure"""
    product_id: int
    size: str
    entry_price: str
    mark_price: str
    unrealized_pnl: str
    margin: str
    leverage: str


@dataclass
class Balance:
    """Balance data structure"""
    asset_id: int
    asset_symbol: str
    available_balance: str
    order_margin: str
    position_margin: str
    commission_balance: str
    unsettled_balance: str


class DeltaExchangeError(Exception):
    """Base exception for Delta Exchange API errors"""
    pass


class DeltaAuthenticationError(DeltaExchangeError):
    """Authentication related errors"""
    pass


class DeltaRateLimitError(DeltaExchangeError):
    """Rate limit related errors"""
    pass


class DeltaNetworkError(DeltaExchangeError):
    """Network related errors"""
    pass


class DeltaExchangeClient:
    """
    Enhanced Delta Exchange API Client for India

    Features:
    - Comprehensive error handling and retry mechanisms
    - Rate limiting compliance
    - Connection pooling
    - Request/response logging
    - Performance monitoring
    - WebSocket support
    """

    def __init__(self):
        self.base_url = settings.delta_base_url
        self.api_key = settings.delta_api_key
        self.api_secret = settings.delta_api_secret
        self.ws_url = settings.delta_ws_url

        # Initialize session with connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'DeltaExchangeTradingBot/1.0.0'
        })

        # WebSocket connection
        self.ws_connection = None
        self.ws_subscriptions = set()

        # Rate limiting (Delta allows 10,000 requests per 5 minutes)
        self.request_count = 0
        self.last_reset_time = time.time()

        logger.info(f"Initialized Delta Exchange Client for {self.base_url}")

    def _generate_signature(self, method: str, request_path: str, query_string: str = "", body: str = "") -> tuple:
        """Generate authentication signature for API requests"""
        timestamp = str(int(time.time() * 1000))
        message = method + timestamp + request_path + query_string + body
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return timestamp, signature

    def _get_headers(self, method: str, request_path: str, query_string: str = "", body: str = "") -> Dict[str, str]:
        """Get headers with authentication for API requests"""
        timestamp, signature = self._generate_signature(method, request_path, query_string, body)

        return {
            'api-key': self.api_key,
            'timestamp': timestamp,
            'signature': signature,
            'Content-Type': 'application/json',
            'User-Agent': 'DeltaExchangeTradingBot/1.0.0'
        }

    @sleep_and_retry
    @limits(calls=100, period=60)  # Rate limit: 100 calls per minute
    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException, DeltaNetworkError),
        max_tries=3,
        max_time=30
    )
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None,
                     data: Optional[Dict] = None, authenticated: bool = True) -> Dict[str, Any]:
        """
        Make HTTP request to Delta Exchange API with comprehensive error handling
        """
        url = f"{self.base_url}{endpoint}"

        # Prepare request parameters
        query_string = ""
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            if query_string:
                query_string = "?" + query_string

        body = ""
        if data:
            body = json.dumps(data)

        # Get headers
        if authenticated:
            headers = self._get_headers(method, endpoint, query_string, body)
        else:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'DeltaExchangeTradingBot/1.0.0'
            }

        # Update rate limiting counter
        current_time = time.time()
        if current_time - self.last_reset_time > 300:  # Reset every 5 minutes
            self.request_count = 0
            self.last_reset_time = current_time

        self.request_count += 1

        # Log request
        logger.debug(f"Making {method} request to {endpoint}")
        if settings.debug:
            logger.debug(f"Headers: {headers}")
            logger.debug(f"Params: {params}")
            logger.debug(f"Data: {data}")

        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                timeout=30
            )

            # Handle response
            if response.status_code == 200:
                result = response.json()
                logger.debug(f"Successful response from {endpoint}")
                return result

            elif response.status_code == 401:
                logger.error(f"Authentication failed for {endpoint}")
                raise DeltaAuthenticationError("Authentication failed - check API credentials")

            elif response.status_code == 429:
                logger.warning(f"Rate limit exceeded for {endpoint}")
                raise DeltaRateLimitError("Rate limit exceeded")

            elif response.status_code >= 500:
                logger.error(f"Server error {response.status_code} for {endpoint}")
                raise DeltaNetworkError(f"Server error: {response.status_code}")

            else:
                logger.error(f"API error {response.status_code} for {endpoint}: {response.text}")
                raise DeltaExchangeError(f"API error {response.status_code}: {response.text}")

        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {endpoint}")
            raise DeltaNetworkError("Request timeout")

        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error for {endpoint}")
            raise DeltaNetworkError("Connection error")

        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception for {endpoint}: {str(e)}")
            raise DeltaNetworkError(f"Request failed: {str(e)}")

    # ==================== PUBLIC MARKET DATA ENDPOINTS ====================

    def get_products(self) -> List[Dict[str, Any]]:
        """Get all trading products"""
        result = self._make_request("GET", "/v2/products", authenticated=False)
        return result.get("result", [])

    def get_product(self, symbol: str) -> Dict[str, Any]:
        """Get specific product details"""
        result = self._make_request("GET", f"/v2/products/{symbol}", authenticated=False)
        return result.get("result", {})

    def get_tickers(self) -> List[Dict[str, Any]]:
        """Get all tickers"""
        result = self._make_request("GET", "/v2/tickers", authenticated=False)
        return result.get("result", [])

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get ticker for specific symbol"""
        result = self._make_request("GET", f"/v2/tickers/{symbol}", authenticated=False)
        return result.get("result", {})

    def get_orderbook(self, product_id: int, depth: int = 20) -> Dict[str, Any]:
        """Get order book for product"""
        params = {"depth": depth}
        result = self._make_request("GET", f"/v2/orderbook/{product_id}", params=params, authenticated=False)
        return result.get("result", {})

    def get_trades(self, product_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent trades for product"""
        params = {"limit": limit}
        result = self._make_request("GET", f"/v2/trades/{product_id}", params=params, authenticated=False)
        return result.get("result", [])

    def get_candles(self, product_id: int, resolution: str = "1m",
                   start: Optional[int] = None, end: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get candlestick data"""
        params = {
            "product_id": product_id,
            "resolution": resolution
        }
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        result = self._make_request("GET", "/v2/history/candles", params=params, authenticated=False)
        return result.get("result", [])

    def get_candles_as_dataframe(self, product_id: int, resolution: str = "1m",
                                start: Optional[int] = None, end: Optional[int] = None) -> pd.DataFrame:
        """Get candlestick data as pandas DataFrame"""
        candles = self.get_candles(product_id, resolution, start, end)

        if not candles:
            return pd.DataFrame()

        df = pd.DataFrame(candles)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df = df.set_index('time')

        # Convert price columns to float
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        if 'volume' in df.columns:
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

        return df

    # ==================== AUTHENTICATED ACCOUNT ENDPOINTS ====================

    def get_balances(self) -> List[Balance]:
        """Get account balances"""
        result = self._make_request("GET", "/v2/wallet/balances")
        balances = result.get("result", [])

        return [
            Balance(
                asset_id=b.get("asset_id"),
                asset_symbol=b.get("asset_symbol"),
                available_balance=b.get("available_balance"),
                order_margin=b.get("order_margin"),
                position_margin=b.get("position_margin"),
                commission_balance=b.get("commission_balance"),
                unsettled_balance=b.get("unsettled_balance")
            ) for b in balances
        ]

    def get_positions(self) -> List[Position]:
        """Get all positions"""
        result = self._make_request("GET", "/v2/positions")
        positions = result.get("result", [])

        return [
            Position(
                product_id=p.get("product_id"),
                size=p.get("size"),
                entry_price=p.get("entry_price"),
                mark_price=p.get("mark_price"),
                unrealized_pnl=p.get("unrealized_pnl"),
                margin=p.get("margin"),
                leverage=p.get("leverage")
            ) for p in positions
        ]

    def get_margined_positions(self) -> List[Position]:
        """Get margined positions"""
        result = self._make_request("GET", "/v2/positions/margined")
        positions = result.get("result", [])

        return [
            Position(
                product_id=p.get("product_id"),
                size=p.get("size"),
                entry_price=p.get("entry_price"),
                mark_price=p.get("mark_price"),
                unrealized_pnl=p.get("unrealized_pnl"),
                margin=p.get("margin"),
                leverage=p.get("leverage")
            ) for p in positions
        ]

    # ==================== ORDER MANAGEMENT ENDPOINTS ====================

    def place_order(self, order: OrderRequest) -> Dict[str, Any]:
        """Place a new order"""
        data = {
            "product_id": order.product_id,
            "side": order.side.value,
            "size": order.size,
            "order_type": order.order_type.value,
            "time_in_force": order.time_in_force.value
        }

        if order.limit_price:
            data["limit_price"] = order.limit_price
        if order.stop_price:
            data["stop_price"] = order.stop_price
        if order.post_only:
            data["post_only"] = order.post_only
        if order.reduce_only:
            data["reduce_only"] = order.reduce_only
        if order.client_order_id:
            data["client_order_id"] = order.client_order_id

        logger.info(f"Placing {order.side.value} order for {order.size} on product {order.product_id}")
        result = self._make_request("POST", "/v2/orders", data=data)

        order_result = result.get("result", {})
        logger.info(f"Order placed successfully: ID {order_result.get('id')}")
        return order_result

    def cancel_order(self, order_id: int, product_id: int) -> Dict[str, Any]:
        """Cancel an order"""
        data = {
            "id": order_id,
            "product_id": product_id
        }

        logger.info(f"Cancelling order {order_id}")
        result = self._make_request("DELETE", "/v2/orders", data=data)

        logger.info(f"Order {order_id} cancelled successfully")
        return result.get("result", {})

    def cancel_all_orders(self, product_id: Optional[int] = None) -> Dict[str, Any]:
        """Cancel all orders"""
        data = {}
        if product_id:
            data["product_id"] = product_id

        logger.info(f"Cancelling all orders{' for product ' + str(product_id) if product_id else ''}")
        result = self._make_request("DELETE", "/v2/orders/all", data=data)

        logger.info("All orders cancelled successfully")
        return result.get("result", {})

    def edit_order(self, order_id: int, product_id: int, **updates) -> Dict[str, Any]:
        """Edit an existing order"""
        data = {
            "id": order_id,
            "product_id": product_id,
            **updates
        }

        logger.info(f"Editing order {order_id}")
        result = self._make_request("PUT", "/v2/orders", data=data)

        logger.info(f"Order {order_id} edited successfully")
        return result.get("result", {})

    def get_active_orders(self, product_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get active orders"""
        params = {}
        if product_id:
            params["product_id"] = product_id

        result = self._make_request("GET", "/v2/orders", params=params)
        return result.get("result", [])

    def get_order_history(self, product_id: Optional[int] = None,
                         states: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get order history"""
        params = {"limit": limit}
        if product_id:
            params["product_id"] = product_id
        if states:
            params["states"] = states

        result = self._make_request("GET", "/v2/orders/history", params=params)
        return result.get("result", [])

    def get_fills(self, product_id: Optional[int] = None,
                 order_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get trade fills"""
        params = {"limit": limit}
        if product_id:
            params["product_id"] = product_id
        if order_id:
            params["order_id"] = order_id

        result = self._make_request("GET", "/v2/fills", params=params)
        return result.get("result", [])

    # ==================== POSITION MANAGEMENT ====================

    def close_position(self, product_id: int) -> Dict[str, Any]:
        """Close a position"""
        data = {"product_id": product_id}

        logger.info(f"Closing position for product {product_id}")
        result = self._make_request("POST", "/v2/positions/close", data=data)

        logger.info(f"Position closed for product {product_id}")
        return result.get("result", {})

    def close_all_positions(self) -> Dict[str, Any]:
        """Close all positions"""
        logger.info("Closing all positions")
        result = self._make_request("DELETE", "/v2/positions")

        logger.info("All positions closed")
        return result.get("result", {})

    def add_margin(self, product_id: int, amount: float) -> Dict[str, Any]:
        """Add margin to position"""
        data = {
            "product_id": product_id,
            "delta_margin": str(amount)
        }

        logger.info(f"Adding {amount} margin to position {product_id}")
        result = self._make_request("POST", "/v2/positions/margin", data=data)

        logger.info(f"Margin added to position {product_id}")
        return result.get("result", {})

    def remove_margin(self, product_id: int, amount: float) -> Dict[str, Any]:
        """Remove margin from position"""
        data = {
            "product_id": product_id,
            "delta_margin": str(-amount)
        }

        logger.info(f"Removing {amount} margin from position {product_id}")
        result = self._make_request("POST", "/v2/positions/margin", data=data)

        logger.info(f"Margin removed from position {product_id}")
        return result.get("result", {})

    # ==================== UTILITY METHODS ====================

    def get_server_time(self) -> Dict[str, Any]:
        """Get server time"""
        result = self._make_request("GET", "/v2/time", authenticated=False)
        return result.get("result", {})

    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            server_time = self.get_server_time()
            return {
                "status": "healthy",
                "server_time": server_time,
                "timestamp": datetime.utcnow().isoformat(),
                "request_count": self.request_count
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "request_count": self.request_count
            }

    def get_account_summary(self) -> Dict[str, Any]:
        """Get comprehensive account summary"""
        try:
            balances = self.get_balances()
            positions = self.get_positions()
            active_orders = self.get_active_orders()

            total_balance = sum(float(b.available_balance) for b in balances if b.available_balance)
            total_margin = sum(float(b.position_margin) for b in balances if b.position_margin)
            total_unrealized_pnl = sum(float(p.unrealized_pnl) for p in positions if p.unrealized_pnl)

            return {
                "balances": [b.__dict__ for b in balances],
                "positions": [p.__dict__ for p in positions],
                "active_orders_count": len(active_orders),
                "summary": {
                    "total_balance": total_balance,
                    "total_margin": total_margin,
                    "total_unrealized_pnl": total_unrealized_pnl,
                    "open_positions": len(positions),
                    "active_orders": len(active_orders)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get account summary: {str(e)}")
            raise

    def __del__(self):
        """Cleanup when object is destroyed"""
        if hasattr(self, 'session'):
            self.session.close()
        if self.ws_connection:
            self.ws_connection.close()