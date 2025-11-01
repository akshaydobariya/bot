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
except ImportError as e:
    print(f"Import error: {e}")
    bot = None

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

if __name__ == '__main__':
    # Get port from environment (for cloud deployment)
    port = int(os.environ.get('PORT', 8000))

    # Run the web interface
    print(f"🌐 Starting web dashboard on port {port}")
    print(f"📊 Dashboard: http://0.0.0.0:{port}")
    print(f"❤️ Health Check: http://0.0.0.0:{port}/health")

    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)