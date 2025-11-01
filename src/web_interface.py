"""
Simple web interface for monitoring the trading bot
This provides a web dashboard to check if the bot is running
"""

from flask import Flask, jsonify, render_template_string, request
import os
import sys
import requests
from datetime import datetime

# Add src to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from main import bot
    from config import settings
    from src.monitoring.metrics import trading_metrics, health_checker
    from database.manager import db_manager
    from src.delta_client import DeltaExchangeClient
except ImportError as e:
    print(f"Import error: {e}")
    bot = None
    DeltaExchangeClient = None

app = Flask(__name__)

# Simple HTML template for the dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Delta Exchange Trading Bot - Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status-healthy { color: #28a745; }
        .status-unhealthy { color: #dc3545; }
        .status-unknown { color: #6c757d; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }
        .metric { text-align: center; padding: 15px; background: #f8f9fa; border-radius: 5px; }
        .metric-value { font-size: 2em; font-weight: bold; color: #007bff; }
        .metric-label { font-size: 0.9em; color: #6c757d; }
        h1, h2 { color: #333; }
        .refresh-btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
        .logs { background: #000; color: #00ff00; padding: 15px; border-radius: 5px; font-family: monospace; max-height: 300px; overflow-y: auto; }
    </style>
    <script>
        function refreshData() {
            location.reload();
        }
        setInterval(refreshData, 30000); // Auto-refresh every 30 seconds
    </script>
</head>
<body>
    <div class="container">
        <h1>🚀 Delta Exchange Trading Bot Dashboard</h1>

        <div class="card">
            <h2>Bot Status</h2>
            <p><strong>Status:</strong> <span class="status-{{ status.health_status }}">{{ status.running_status }}</span></p>
            <p><strong>Uptime:</strong> {{ status.uptime }}</p>
            <p><strong>Environment:</strong> {{ config.environment }}</p>
            <p><strong>Strategy:</strong> {{ config.strategy }}</p>
            <p><strong>Symbol:</strong> {{ config.symbol }}</p>
            <button class="refresh-btn" onclick="refreshData()">🔄 Refresh</button>
        </div>

        <div class="card">
            <h2>Trading Metrics</h2>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value">{{ metrics.total_trades }}</div>
                    <div class="metric-label">Total Trades</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${{ "%.2f"|format(metrics.portfolio_value) }}</div>
                    <div class="metric-label">Portfolio Value</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${{ "%.2f"|format(metrics.daily_pnl) }}</div>
                    <div class="metric-label">Daily P&L</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{{ "%.1f"|format(metrics.win_rate) }}%</div>
                    <div class="metric-label">Win Rate</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Risk Metrics</h2>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value">{{ metrics.risk_level }}</div>
                    <div class="metric-label">Risk Level</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{{ metrics.open_positions }}</div>
                    <div class="metric-label">Open Positions</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{{ "%.1f"|format(metrics.drawdown) }}%</div>
                    <div class="metric-label">Drawdown</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${{ "%.0f"|format(metrics.exposure) }}</div>
                    <div class="metric-label">Total Exposure</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Recent Activity</h2>
            <div class="logs">{{ recent_logs | safe }}</div>
        </div>

        <div class="card">
            <h2>API Endpoints</h2>
            <ul>
                <li><a href="/health">/health</a> - Health check</li>
                <li><a href="/status">/status</a> - Bot status JSON</li>
                <li><a href="/metrics">/metrics</a> - Prometheus metrics</li>
                <li><a href="/api/trades">/api/trades</a> - Recent trades</li>
            </ul>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    """Main dashboard page"""
    try:
        # Get bot status
        if bot:
            status_data = bot.get_status()
            running_status = "🟢 Running" if status_data.get('running', False) else "🔴 Stopped"
        else:
            status_data = {}
            running_status = "🟡 Loading"

        # Get configuration
        config_data = {
            'environment': getattr(settings, 'environment', 'unknown'),
            'strategy': getattr(settings, 'strategy', 'unknown'),
            'symbol': getattr(settings, 'default_symbol', 'unknown')
        }

        # Get metrics
        try:
            metrics_summary = trading_metrics.get_metrics_summary()
            metrics_data = {
                'total_trades': metrics_summary.get('trading', {}).get('total_trades', 0),
                'portfolio_value': metrics_summary.get('portfolio', {}).get('value', 0),
                'daily_pnl': metrics_summary.get('portfolio', {}).get('daily_pnl', 0),
                'win_rate': 0,  # Would need to calculate from trade history
                'risk_level': ['Low', 'Medium', 'High', 'Critical'][int(metrics_summary.get('risk', {}).get('level', 1))],
                'open_positions': metrics_summary.get('risk', {}).get('position_count', 0),
                'drawdown': metrics_summary.get('portfolio', {}).get('drawdown', 0),
                'exposure': metrics_summary.get('risk', {}).get('total_exposure', 0)
            }
        except:
            metrics_data = {
                'total_trades': 0, 'portfolio_value': 0, 'daily_pnl': 0, 'win_rate': 0,
                'risk_level': 'Unknown', 'open_positions': 0, 'drawdown': 0, 'exposure': 0
            }

        # Get recent logs (simplified)
        recent_logs = "Bot is initializing...<br>Connecting to Delta Exchange API...<br>Starting trading strategies..."

        # Get health status
        health_status = health_checker.get_health_status() if health_checker else 'unknown'

        return render_template_string(DASHBOARD_HTML,
                                    status={
                                        'running_status': running_status,
                                        'uptime': status_data.get('uptime_formatted', 'Unknown'),
                                        'health_status': health_status
                                    },
                                    config=config_data,
                                    metrics=metrics_data,
                                    recent_logs=recent_logs)

    except Exception as e:
        return f"Dashboard Error: {str(e)}", 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        if bot:
            status = bot.get_status()
            is_healthy = status.get('running', False)
        else:
            is_healthy = False

        return jsonify({
            'status': 'healthy' if is_healthy else 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'delta-trading-bot'
        }), 200 if is_healthy else 503

    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/status')
def bot_status():
    """Get bot status as JSON"""
    try:
        if bot:
            return jsonify(bot.get_status())
        else:
            return jsonify({
                'running': False,
                'error': 'Bot not initialized',
                'timestamp': datetime.now().isoformat()
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    try:
        if trading_metrics:
            # Return basic metrics in Prometheus format
            metrics_summary = trading_metrics.get_metrics_summary()

            prometheus_output = f"""# HELP trading_bot_status Bot running status
# TYPE trading_bot_status gauge
trading_bot_status{{service="delta-trading-bot"}} {1 if bot and bot.running else 0}

# HELP trading_bot_uptime_seconds Bot uptime in seconds
# TYPE trading_bot_uptime_seconds counter
trading_bot_uptime_seconds{{service="delta-trading-bot"}} {metrics_summary.get('uptime_seconds', 0)}

# HELP trading_bot_portfolio_value Current portfolio value
# TYPE trading_bot_portfolio_value gauge
trading_bot_portfolio_value{{service="delta-trading-bot"}} {metrics_summary.get('portfolio', {}).get('value', 0)}

# HELP trading_bot_total_trades Total number of trades
# TYPE trading_bot_total_trades counter
trading_bot_total_trades{{service="delta-trading-bot"}} {metrics_summary.get('trading', {}).get('total_trades', 0)}
"""
            return prometheus_output, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            return "# No metrics available\n", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except Exception as e:
        return f"# Error: {str(e)}\n", 500, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/api/trades')
def recent_trades():
    """Get recent trades"""
    try:
        if db_manager:
            trades = db_manager.get_trades(limit=10)
            trade_data = []
            for trade in trades:
                trade_data.append({
                    'id': trade.id,
                    'symbol': trade.symbol,
                    'side': trade.side,
                    'size': trade.size,
                    'price': trade.price,
                    'executed_at': trade.executed_at.isoformat() if trade.executed_at else None,
                    'strategy': trade.strategy_name,
                    'pnl': trade.realized_pnl
                })
            return jsonify(trade_data)
        else:
            return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config')
def get_config():
    """Get bot configuration"""
    try:
        config_data = {
            'environment': getattr(settings, 'environment', 'unknown'),
            'strategy': getattr(settings, 'strategy', 'sma_crossover'),
            'symbol': getattr(settings, 'default_symbol', 'BTCUSD'),
            'risk_percentage': getattr(settings, 'risk_percentage', 1.0),
            'stop_loss_percentage': getattr(settings, 'stop_loss_percentage', 2.0),
            'max_daily_loss': getattr(settings, 'max_daily_loss', 100.0),
            'paper_trading': getattr(settings, 'enable_paper_trading', False)
        }
        return jsonify(config_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ip-info')
def get_ip_info():
    """Get server IP information for Delta Exchange whitelist"""
    try:
        # Get public IP address
        try:
            response = requests.get('https://httpbin.org/ip', timeout=10)
            public_ip = response.json().get('origin', 'Unknown')
        except:
            try:
                response = requests.get('https://ipapi.co/ip/', timeout=10)
                public_ip = response.text.strip()
            except:
                public_ip = 'Unable to determine'

        # Get client IP (from Railway/proxy)
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)

        ip_info = {
            'public_ip': public_ip,
            'client_ip': client_ip,
            'headers': dict(request.headers),
            'message': 'Add the public_ip to your Delta Exchange API whitelist',
            'instructions': [
                '1. Go to Delta Exchange → API Management',
                '2. Find your API key settings',
                '3. Add this IP to the whitelist:',
                f'   {public_ip}',
                '4. Or use 0.0.0.0/0 to allow all IPs (less secure)'
            ]
        }
        return jsonify(ip_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/credentials-status')
def check_credentials():
    """Check API credentials status"""
    try:
        status = settings.get_api_credentials_status()
        status.update({
            'message': 'API credentials configuration status',
            'instructions': [
                '1. Go to Railway Dashboard → Your Project',
                '2. Click Variables tab',
                '3. Add these environment variables:',
                '   DELTA_API_KEY=Jx3GNFer1ryFMA3c9t1m1DIt0w6ZqV',
                '   DELTA_API_SECRET=h2gGqrnc5nrvwQza2LgurFH1w0RSw0BtfSATKn5CKgySHqwDK5FmUpCKdbz',
                '   WEB_MODE=true',
                '4. Redeploy your bot'
            ]
        })
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-delta-connection')
def test_delta_connection():
    """Comprehensive Delta Exchange API connection test"""
    try:
        import hashlib
        import hmac
        import time
        import json

        # Get API credentials
        api_key = os.environ.get('DELTA_API_KEY')
        api_secret = os.environ.get('DELTA_API_SECRET')

        if not api_key or not api_secret:
            return jsonify({
                'status': 'error',
                'issue': 'missing_credentials',
                'message': 'API credentials not found in environment variables',
                'api_key_present': bool(api_key),
                'api_secret_present': bool(api_secret),
                'fix': 'Add DELTA_API_KEY and DELTA_API_SECRET to Railway environment variables'
            }), 400

        # Test 1: Basic connectivity (no auth required)
        test_results = {
            'timestamp': datetime.now().isoformat(),
            'api_key_length': len(api_key) if api_key else 0,
            'api_secret_length': len(api_secret) if api_secret else 0,
            'tests': {}
        }

        # Test basic connectivity to Delta Exchange
        try:
            response = requests.get('https://api.india.delta.exchange/v2/products', timeout=10)
            test_results['tests']['basic_connectivity'] = {
                'status': 'success' if response.status_code == 200 else 'failed',
                'status_code': response.status_code,
                'response_size': len(response.text),
                'message': 'Can reach Delta Exchange API'
            }
        except Exception as e:
            test_results['tests']['basic_connectivity'] = {
                'status': 'failed',
                'error': str(e),
                'message': 'Cannot reach Delta Exchange API - network issue'
            }

        # Test 2: Authentication test (wallet endpoint)
        try:
            # Create signed request to wallet endpoint (Fixed: timestamp in seconds)
            timestamp = str(int(time.time()))  # Seconds only, not milliseconds!
            method = 'GET'
            path = '/v2/wallet/balances'
            query_string = ''  # No query parameters
            body = ''  # No request body for GET

            # Create signature (method + timestamp + path + query_string + body)
            payload = method + timestamp + path + query_string + body
            signature = hmac.new(
                api_secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            headers = {
                'api-key': api_key,
                'timestamp': timestamp,
                'signature': signature,
                'User-Agent': 'DeltaTradingBot/1.0',
                'Content-Type': 'application/json'
            }

            response = requests.get(
                f'https://api.india.delta.exchange{path}',
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                test_results['tests']['authentication'] = {
                    'status': 'success',
                    'status_code': response.status_code,
                    'message': 'API credentials are valid and working',
                    'wallet_data': response.json()
                }
            elif response.status_code == 403:
                test_results['tests']['authentication'] = {
                    'status': 'ip_blocked',
                    'status_code': response.status_code,
                    'error': response.text,
                    'message': 'IP address not whitelisted in Delta Exchange',
                    'fix': 'Add your server IP to Delta Exchange API whitelist'
                }
            elif response.status_code == 401:
                test_results['tests']['authentication'] = {
                    'status': 'auth_failed',
                    'status_code': response.status_code,
                    'error': response.text,
                    'message': 'Invalid API credentials or signature',
                    'fix': 'Check API key and secret are correct'
                }
            else:
                test_results['tests']['authentication'] = {
                    'status': 'unknown_error',
                    'status_code': response.status_code,
                    'error': response.text,
                    'message': f'Unexpected response: {response.status_code}'
                }

        except Exception as e:
            test_results['tests']['authentication'] = {
                'status': 'failed',
                'error': str(e),
                'message': 'Failed to create authenticated request'
            }

        # Test 3: Public endpoint test (should always work)
        try:
            response = requests.get('https://api.india.delta.exchange/v2/products/BTCUSD', timeout=10)
            test_results['tests']['public_endpoint'] = {
                'status': 'success' if response.status_code == 200 else 'failed',
                'status_code': response.status_code,
                'message': 'Public endpoint accessibility'
            }
        except Exception as e:
            test_results['tests']['public_endpoint'] = {
                'status': 'failed',
                'error': str(e)
            }

        # Determine overall diagnosis
        auth_test = test_results['tests'].get('authentication', {})
        if auth_test.get('status') == 'success':
            test_results['diagnosis'] = 'connection_working'
            test_results['message'] = '✅ All tests passed! API connection is working properly.'
        elif auth_test.get('status') == 'ip_blocked':
            test_results['diagnosis'] = 'ip_whitelist_issue'
            test_results['message'] = '🚫 IP address blocked. Add your server IP to Delta Exchange whitelist.'
        elif auth_test.get('status') == 'auth_failed':
            test_results['diagnosis'] = 'credential_issue'
            test_results['message'] = '🔑 API credentials invalid. Check your API key and secret.'
        else:
            test_results['diagnosis'] = 'unknown_issue'
            test_results['message'] = '❓ Connection issue detected. Check logs for details.'

        return jsonify(test_results)

    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': 'Failed to run connection tests'
        }), 500

@app.route('/api/balance')
def get_balance():
    """Get Delta Exchange wallet balance (diagnostic endpoint)"""
    try:
        import hashlib
        import hmac
        import time

        # Get API credentials
        api_key = os.environ.get('DELTA_API_KEY')
        api_secret = os.environ.get('DELTA_API_SECRET')

        if not api_key or not api_secret:
            return jsonify({
                'error': 'API credentials not configured',
                'message': 'Set DELTA_API_KEY and DELTA_API_SECRET in Railway environment variables'
            }), 400

        # Create signed request (timestamp in SECONDS, not milliseconds!)
        timestamp = str(int(time.time()))  # Seconds only, as per Delta Exchange docs
        method = 'GET'
        path = '/v2/wallet/balances'
        query_string = ''  # No query parameters
        body = ''  # No request body for GET

        # Create signature (method + timestamp + path + query_string + body)
        payload = method + timestamp + path + query_string + body
        signature = hmac.new(
            api_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        headers = {
            'api-key': api_key,
            'timestamp': timestamp,
            'signature': signature,
            'User-Agent': 'DeltaTradingBot/1.0',
            'Content-Type': 'application/json'
        }

        response = requests.get(
            f'https://api.india.delta.exchange{path}',
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'status': 'success',
                'balances': data.get('result', []),
                'message': 'Successfully retrieved wallet balance'
            })
        else:
            return jsonify({
                'status': 'error',
                'status_code': response.status_code,
                'error': response.text,
                'error_json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None,
                'headers_sent': dict(headers),
                'payload_used': payload,
                'message': 'Failed to retrieve balance from Delta Exchange'
            }), 200  # Return 200 so we can see the error details

    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': 'Failed to connect to Delta Exchange API'
        }), 500

@app.route('/api/debug-auth')
def debug_auth():
    """Debug authentication process step by step"""
    try:
        import hashlib
        import hmac
        import time

        # Get API credentials
        api_key = os.environ.get('DELTA_API_KEY')
        api_secret = os.environ.get('DELTA_API_SECRET')

        debug_info = {
            'step1_credentials': {
                'api_key': api_key[:10] + '...' if api_key else None,
                'api_secret': api_secret[:10] + '...' if api_secret else None,
                'api_key_length': len(api_key) if api_key else 0,
                'api_secret_length': len(api_secret) if api_secret else 0
            }
        }

        if not api_key or not api_secret:
            debug_info['error'] = 'Missing credentials'
            return jsonify(debug_info)

        # Test different API endpoints (Fixed: use seconds for timestamp)
        current_time = int(time.time())  # Seconds, not milliseconds
        timestamp = str(current_time)

        debug_info['step2_timing'] = {
            'current_timestamp': timestamp,
            'current_time_readable': datetime.fromtimestamp(current_time).isoformat()
        }

        # Test 1: Try a simple public endpoint first
        try:
            response = requests.get('https://api.india.delta.exchange/v2/products/BTCUSD', timeout=10)
            debug_info['step3_public_test'] = {
                'status': 'success' if response.status_code == 200 else 'failed',
                'status_code': response.status_code,
                'response_size': len(response.text)
            }
        except Exception as e:
            debug_info['step3_public_test'] = {'error': str(e)}

        # Test 2: Try authenticated endpoint with detailed signature debug
        method = 'GET'
        path = '/v2/wallet/balances'
        query_string = ''  # No query parameters
        body = ''  # No request body for GET
        payload = method + timestamp + path + query_string + body

        debug_info['step4_signature_creation'] = {
            'method': method,
            'timestamp': timestamp,
            'path': path,
            'payload': payload,
            'payload_length': len(payload)
        }

        # Create signature
        signature = hmac.new(
            api_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        debug_info['step5_signature'] = {
            'signature': signature[:20] + '...',
            'signature_length': len(signature)
        }

        headers = {
            'api-key': api_key,
            'timestamp': timestamp,
            'signature': signature,
            'User-Agent': 'DeltaTradingBot/1.0',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.get(
                f'https://api.india.delta.exchange{path}',
                headers=headers,
                timeout=10
            )

            debug_info['step6_auth_test'] = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'response_text': response.text[:500] if response.text else None
            }

            if response.headers.get('content-type', '').startswith('application/json'):
                try:
                    debug_info['step6_auth_test']['response_json'] = response.json()
                except:
                    pass

        except Exception as e:
            debug_info['step6_auth_test'] = {'error': str(e)}

        return jsonify(debug_info)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# NEW OFFICIAL DELTA EXCHANGE API ENDPOINTS

@app.route('/api/delta/test-official')
def test_official_delta():
    """Test Delta Exchange using official client implementation"""
    try:
        if not DeltaExchangeClient:
            return jsonify({
                'error': 'DeltaExchangeClient not available',
                'message': 'Import failed'
            }), 500

        client = DeltaExchangeClient()
        result = client.test_connection()

        return jsonify({
            'status': 'success',
            'implementation': 'Official Delta Exchange India Client',
            'test_results': result,
            'server_info': client.get_server_info()
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': 'Failed to initialize Delta Exchange client'
        }), 500

@app.route('/api/delta/products')
def get_delta_products():
    """Get all Delta Exchange products using official client"""
    try:
        client = DeltaExchangeClient()
        result = client.get_products()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delta/products/<symbol>')
def get_delta_product(symbol):
    """Get specific Delta Exchange product"""
    try:
        client = DeltaExchangeClient()
        result = client.get_product(symbol)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delta/ticker/<symbol>')
def get_delta_ticker(symbol):
    """Get real-time ticker for a symbol"""
    try:
        client = DeltaExchangeClient()
        result = client.get_ticker(symbol)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delta/wallet')
def get_delta_wallet():
    """Get wallet balances using official client"""
    try:
        client = DeltaExchangeClient()
        result = client.get_wallet_balances()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delta/positions')
def get_delta_positions():
    """Get current positions"""
    try:
        client = DeltaExchangeClient()
        result = client.get_positions()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delta/orders')
def get_delta_orders():
    """Get order history"""
    try:
        client = DeltaExchangeClient()
        limit = request.args.get('limit', 50, type=int)
        result = client.get_orders(limit=limit)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delta/active-orders')
def get_delta_active_orders():
    """Get active orders"""
    try:
        client = DeltaExchangeClient()
        result = client.get_active_orders()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delta/candles/<symbol>')
def get_delta_candles(symbol):
    """Get historical candlestick data"""
    try:
        client = DeltaExchangeClient()
        resolution = request.args.get('resolution', '1h')
        start = request.args.get('start')
        end = request.args.get('end')

        result = client.get_candles(symbol, resolution, start, end)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delta/server-info')
def get_delta_server_info():
    """Get server and connection information"""
    try:
        client = DeltaExchangeClient()
        result = client.get_server_info()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delta/ip-monitor')
def monitor_ip_changes():
    """Monitor IP changes and provide whitelist instructions"""
    try:
        # Get current IPs
        try:
            ip_response = requests.get('https://httpbin.org/ip', timeout=5)
            current_ip = ip_response.json().get('origin', 'Unknown')
        except:
            current_ip = 'Unable to determine'

        # Get headers info
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        real_ip = request.environ.get('HTTP_X_REAL_IP', 'Unknown')

        # Previous known IPs that were whitelisted
        known_ips = [
            '162.220.232.43',
            '152.59.33.106',
            '162.220.232.102'
        ]

        ip_status = {
            'current_public_ip': current_ip,
            'client_ip': client_ip,
            'real_ip': real_ip,
            'known_whitelisted_ips': known_ips,
            'ip_changed': current_ip not in known_ips,
            'timestamp': datetime.now().isoformat()
        }

        if ip_status['ip_changed']:
            ip_status['action_required'] = {
                'message': f'⚠️ New IP detected: {current_ip}',
                'instructions': [
                    '1. Go to Delta Exchange → API Management',
                    '2. Find your API key: FcnplGp0tyMHXvtXzYWNlA9n1YezjU',
                    '3. Edit IP Whitelist',
                    f'4. Add this new IP: {current_ip}',
                    '5. Save changes and wait 2-3 minutes'
                ],
                'alternative': f'Or add IP range: {current_ip.rsplit(".", 1)[0]}.0/24 to allow entire range'
            }
        else:
            ip_status['status'] = f'✅ Current IP {current_ip} should be whitelisted'

        return jsonify(ip_status)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delta/test-and-guide')
def test_and_provide_guidance():
    """Test authentication and provide specific guidance based on results"""
    try:
        client = DeltaExchangeClient()

        # Test authentication
        wallet_result = client.get_wallet_balances()

        guidance = {
            'timestamp': datetime.now().isoformat(),
            'test_result': wallet_result,
            'diagnosis': '',
            'instructions': []
        }

        if wallet_result.get('success'):
            guidance['diagnosis'] = '✅ WORKING PERFECTLY!'
            guidance['instructions'] = [
                '🎉 Your Delta Exchange API connection is working!',
                '💰 You can now access wallet balances',
                '📊 All trading endpoints should be functional',
                '🤖 Your automated trading bot is ready!'
            ]
        elif wallet_result.get('status_code') == 401:
            error_data = wallet_result.get('error', {})
            if 'invalid_api_key' in str(error_data):
                # Get current IP for instructions
                try:
                    ip_response = requests.get('https://httpbin.org/ip', timeout=5)
                    current_ip = ip_response.json().get('origin', 'Unknown')
                except:
                    current_ip = 'Unable to determine'

                guidance['diagnosis'] = '🚫 IP WHITELIST ISSUE'
                guidance['current_ip'] = current_ip
                guidance['instructions'] = [
                    f'📍 Your server IP is: {current_ip}',
                    '🔧 This IP needs to be whitelisted in Delta Exchange',
                    '',
                    '📝 Steps to fix:',
                    '1. Go to https://app.india.delta.exchange',
                    '2. Navigate to API Management',
                    '3. Find your API key: FcnplGp0tyMHXvtXzYWNlA9n1YezjU',
                    '4. Click "Edit" or "Manage"',
                    '5. Add to IP Whitelist: ' + current_ip,
                    '6. Save changes',
                    '7. Wait 2-3 minutes for changes to take effect',
                    '',
                    '🔄 Then test again at: /api/delta/test-and-guide'
                ]
            else:
                guidance['diagnosis'] = '🔑 CREDENTIAL ISSUE'
                guidance['instructions'] = [
                    '❌ API credentials are invalid or expired',
                    '🔄 Try regenerating your API key in Delta Exchange',
                    '⚙️ Update Railway environment variables with new credentials'
                ]
        else:
            guidance['diagnosis'] = f'❓ UNKNOWN ISSUE (Status: {wallet_result.get("status_code", "unknown")})'
            guidance['instructions'] = [
                '🔍 Unexpected error occurred',
                '📋 Check the test_result for more details',
                '💬 Contact Delta Exchange support if needed'
            ]

        return jsonify(guidance)

    except Exception as e:
        return jsonify({
            'diagnosis': '💥 SYSTEM ERROR',
            'error': str(e),
            'instructions': [
                '⚠️ Bot system error occurred',
                '🔧 Check server logs for details',
                '🔄 Try redeploying if needed'
            ]
        }), 500

if __name__ == '__main__':
    # Get port from environment (for cloud deployment)
    port = int(os.environ.get('PORT', 8000))

    # Run the web interface
    print(f"🌐 Starting web dashboard on port {port}")
    print(f"📊 Dashboard: http://0.0.0.0:{port}")
    print(f"❤️ Health Check: http://0.0.0.0:{port}/health")

    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)