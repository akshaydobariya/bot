"""
Delta Exchange India API Client
Implemented according to official documentation:
https://deltaexchangeindia.freshdesk.com/support/solutions/articles/80001174969
"""

import requests
import hashlib
import hmac
import time
import json
import os
from typing import Dict, Any, Optional


class DeltaExchangeClient:
    """Official Delta Exchange India API Client"""

    def __init__(self, api_key: str = None, api_secret: str = None):
        """Initialize Delta Exchange client with API credentials"""
        self.api_key = api_key or os.environ.get('DELTA_API_KEY')
        self.api_secret = api_secret or os.environ.get('DELTA_API_SECRET')
        self.base_url = 'https://api.india.delta.exchange'
        self.user_agent = 'DeltaTradingBot/1.0'

        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret are required. Set DELTA_API_KEY and DELTA_API_SECRET environment variables.")

    def _create_signature(self, method: str, timestamp: str, path: str,
                         query_string: str = '', body: str = '') -> str:
        """
        Create signature according to Delta Exchange official documentation:
        Concatenate: method + timestamp + path + query_string + body
        Then generate HMAC-SHA256 hash using API secret
        """
        payload = method + timestamp + path + query_string + body
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _make_request(self, method: str, path: str, query_params: Dict = None,
                     body_data: Any = None) -> Dict:
        """
        Make authenticated request to Delta Exchange API
        Following official documentation specifications
        """
        # Create timestamp in seconds (as per documentation)
        timestamp = str(int(time.time()))

        # Prepare query string
        query_string = ''
        if query_params:
            params = '&'.join([f"{k}={v}" for k, v in query_params.items()])
            query_string = f'?{params}'

        # Prepare request body
        body = ''
        if body_data:
            body = json.dumps(body_data) if isinstance(body_data, dict) else str(body_data)

        # Create signature according to official specs
        signature = self._create_signature(method, timestamp, path, query_string, body)

        # Official headers format
        headers = {
            'api-key': self.api_key,
            'timestamp': timestamp,
            'signature': signature,
            'User-Agent': self.user_agent
        }

        # Add Content-Type for POST/PUT requests
        if method in ['POST', 'PUT', 'PATCH'] and body_data:
            headers['Content-Type'] = 'application/json'

        # Construct full URL
        url = f'{self.base_url}{path}{query_string}'

        try:
            # Make the request
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=body if body else None,
                timeout=10
            )

            # Return structured response
            result = {
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'headers': dict(response.headers),
                'url': url,
                'method': method,
                'timestamp': timestamp,
                'signature_payload': method + timestamp + path + query_string + body
            }

            # Parse response data
            try:
                result['data'] = response.json()
            except:
                result['text'] = response.text

            # Add error information for non-200 responses
            if response.status_code != 200:
                result['error'] = {
                    'code': response.status_code,
                    'message': response.text,
                    'json': None
                }
                try:
                    result['error']['json'] = response.json()
                except:
                    pass

            return result

        except Exception as e:
            return {
                'status_code': 500,
                'success': False,
                'error': {
                    'code': 500,
                    'message': str(e),
                    'type': 'request_exception'
                },
                'url': url,
                'method': method,
                'timestamp': timestamp
            }

    # Public Endpoints (No Authentication Required)

    def get_products(self) -> Dict:
        """Get all trading products/instruments"""
        return self._make_request('GET', '/v2/products')

    def get_product(self, symbol: str) -> Dict:
        """Get specific product information"""
        return self._make_request('GET', f'/v2/products/{symbol}')

    def get_ticker(self, symbol: str) -> Dict:
        """Get real-time ticker data for a symbol"""
        return self._make_request('GET', f'/v2/tickers/{symbol}')

    def get_candles(self, symbol: str, resolution: str = '1h',
                   start: str = None, end: str = None) -> Dict:
        """
        Get historical candlestick data

        Args:
            symbol: Trading symbol (e.g., 'BTCUSD')
            resolution: Time resolution ('1m', '5m', '15m', '1h', '4h', '1d')
            start: Start timestamp (Unix seconds)
            end: End timestamp (Unix seconds)
        """
        params = {
            'symbol': symbol,
            'resolution': resolution
        }
        if start:
            params['start'] = start
        if end:
            params['end'] = end

        return self._make_request('GET', '/v2/history/candles', query_params=params)

    # Authenticated Endpoints

    def get_wallet_balances(self) -> Dict:
        """Get wallet balances (requires authentication)"""
        return self._make_request('GET', '/v2/wallet/balances')

    def get_positions(self) -> Dict:
        """Get current positions"""
        return self._make_request('GET', '/v2/positions')

    def get_orders(self, limit: int = 100) -> Dict:
        """Get order history"""
        params = {'limit': limit}
        return self._make_request('GET', '/v2/orders/history', query_params=params)

    def get_active_orders(self) -> Dict:
        """Get active/open orders"""
        return self._make_request('GET', '/v2/orders')

    def place_order(self, symbol: str, side: str, size: float,
                   order_type: str = 'market', price: float = None) -> Dict:
        """
        Place a new order

        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            size: Order size/quantity
            order_type: 'market' or 'limit'
            price: Required for limit orders
        """
        order_data = {
            'product_symbol': symbol,
            'side': side,
            'size': str(size),
            'order_type': order_type
        }

        if order_type == 'limit' and price:
            order_data['limit_price'] = str(price)

        return self._make_request('POST', '/v2/orders', body_data=order_data)

    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an existing order"""
        return self._make_request('DELETE', f'/v2/orders/{order_id}')

    def cancel_all_orders(self, symbol: str = None) -> Dict:
        """Cancel all orders (optionally for a specific symbol)"""
        body_data = {}
        if symbol:
            body_data['product_symbol'] = symbol
        return self._make_request('DELETE', '/v2/orders/all', body_data=body_data)

    # Utility Methods

    def test_connection(self) -> Dict:
        """Comprehensive connection test"""
        results = {
            'timestamp': time.time(),
            'tests': {},
            'overall_status': 'unknown'
        }

        # Test 1: Public endpoint
        try:
            products = self.get_products()
            results['tests']['public_endpoint'] = {
                'status': 'success' if products['success'] else 'failed',
                'status_code': products['status_code'],
                'message': 'Public products endpoint'
            }
        except Exception as e:
            results['tests']['public_endpoint'] = {
                'status': 'failed',
                'error': str(e),
                'message': 'Failed to reach public endpoint'
            }

        # Test 2: Authentication
        try:
            wallet = self.get_wallet_balances()
            if wallet['success']:
                results['tests']['authentication'] = {
                    'status': 'success',
                    'status_code': wallet['status_code'],
                    'message': 'Authentication successful',
                    'balances': wallet.get('data', {}).get('result', [])
                }
                results['overall_status'] = 'success'
            elif wallet['status_code'] == 401:
                results['tests']['authentication'] = {
                    'status': 'auth_failed',
                    'status_code': wallet['status_code'],
                    'message': 'Invalid API credentials',
                    'error': wallet.get('error', {}),
                    'signature_payload': wallet.get('signature_payload')
                }
                results['overall_status'] = 'auth_failed'
            elif wallet['status_code'] == 403:
                results['tests']['authentication'] = {
                    'status': 'ip_blocked',
                    'status_code': wallet['status_code'],
                    'message': 'IP address not whitelisted',
                    'error': wallet.get('error', {})
                }
                results['overall_status'] = 'ip_blocked'
            else:
                results['tests']['authentication'] = {
                    'status': 'unknown_error',
                    'status_code': wallet['status_code'],
                    'message': 'Unexpected authentication error',
                    'error': wallet.get('error', {})
                }
                results['overall_status'] = 'error'
        except Exception as e:
            results['tests']['authentication'] = {
                'status': 'exception',
                'error': str(e),
                'message': 'Exception during authentication test'
            }
            results['overall_status'] = 'error'

        return results

    def get_server_info(self) -> Dict:
        """Get server and connection information"""
        try:
            # Get public IP
            ip_response = requests.get('https://httpbin.org/ip', timeout=5)
            public_ip = ip_response.json().get('origin', 'Unknown')
        except:
            public_ip = 'Unable to determine'

        return {
            'api_key_length': len(self.api_key) if self.api_key else 0,
            'api_secret_length': len(self.api_secret) if self.api_secret else 0,
            'base_url': self.base_url,
            'user_agent': self.user_agent,
            'public_ip': public_ip,
            'timestamp': int(time.time())
        }


# Convenience function for quick testing
def quick_test():
    """Quick test function for Delta Exchange API"""
    try:
        client = DeltaExchangeClient()
        return client.test_connection()
    except Exception as e:
        return {
            'error': str(e),
            'status': 'failed_to_initialize'
        }


if __name__ == '__main__':
    # Test the client
    result = quick_test()
    print(json.dumps(result, indent=2))