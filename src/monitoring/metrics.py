"""
Prometheus Metrics and Monitoring for Delta Exchange Trading Bot

This module provides comprehensive monitoring capabilities including:
- Performance metrics collection
- Prometheus integration
- Health checks
- Real-time dashboards
- Alert management
"""

import time
import psutil
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from threading import Thread
import threading

from prometheus_client import (
    Counter, Histogram, Gauge, Summary,
    start_http_server, CollectorRegistry, REGISTRY
)

from src.config import settings
from src.utils.logger import trading_logger, logger


class TradingMetrics:
    """
    Comprehensive metrics collection for trading bot

    Provides:
    - Trading performance metrics
    - System performance monitoring
    - API response time tracking
    - Error rate monitoring
    - Risk metrics tracking
    """

    def __init__(self):
        # Trading Metrics
        self.trades_total = Counter(
            'trading_bot_trades_total',
            'Total number of trades executed',
            ['side', 'symbol', 'strategy', 'status']
        )

        self.trade_pnl = Histogram(
            'trading_bot_trade_pnl',
            'Profit/Loss per trade',
            ['symbol', 'strategy'],
            buckets=(-1000, -500, -100, -50, -10, 0, 10, 50, 100, 500, 1000, float('inf'))
        )

        self.position_size = Histogram(
            'trading_bot_position_size',
            'Position sizes',
            ['symbol'],
            buckets=(0.001, 0.01, 0.1, 0.5, 1.0, 5.0, 10.0, float('inf'))
        )

        self.signals_generated = Counter(
            'trading_bot_signals_total',
            'Total signals generated',
            ['signal_type', 'strategy', 'symbol']
        )

        self.signal_strength = Histogram(
            'trading_bot_signal_strength',
            'Signal strength distribution',
            ['signal_type', 'strategy'],
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
        )

        # Performance Metrics
        self.portfolio_value = Gauge(
            'trading_bot_portfolio_value',
            'Current portfolio value'
        )

        self.unrealized_pnl = Gauge(
            'trading_bot_unrealized_pnl',
            'Unrealized profit/loss'
        )

        self.daily_pnl = Gauge(
            'trading_bot_daily_pnl',
            'Daily profit/loss'
        )

        self.drawdown = Gauge(
            'trading_bot_drawdown_percent',
            'Current drawdown percentage'
        )

        self.win_rate = Gauge(
            'trading_bot_win_rate',
            'Win rate percentage',
            ['strategy', 'timeframe']
        )

        # API Metrics
        self.api_requests_total = Counter(
            'trading_bot_api_requests_total',
            'Total API requests',
            ['endpoint', 'method', 'status']
        )

        self.api_request_duration = Histogram(
            'trading_bot_api_request_duration_seconds',
            'API request duration',
            ['endpoint', 'method'],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf'))
        )

        self.api_errors = Counter(
            'trading_bot_api_errors_total',
            'API errors',
            ['endpoint', 'error_type']
        )

        self.rate_limit_hits = Counter(
            'trading_bot_rate_limit_hits_total',
            'Rate limit hits'
        )

        # System Metrics
        self.system_cpu_usage = Gauge(
            'trading_bot_cpu_usage_percent',
            'CPU usage percentage'
        )

        self.system_memory_usage = Gauge(
            'trading_bot_memory_usage_bytes',
            'Memory usage in bytes'
        )

        self.system_uptime = Gauge(
            'trading_bot_uptime_seconds',
            'Bot uptime in seconds'
        )

        # Risk Metrics
        self.risk_level = Gauge(
            'trading_bot_risk_level',
            'Current risk level (0=low, 1=medium, 2=high, 3=critical)'
        )

        self.max_drawdown = Gauge(
            'trading_bot_max_drawdown_percent',
            'Maximum drawdown percentage'
        )

        self.position_count = Gauge(
            'trading_bot_open_positions',
            'Number of open positions'
        )

        self.total_exposure = Gauge(
            'trading_bot_total_exposure',
            'Total portfolio exposure'
        )

        # Error Metrics
        self.errors_total = Counter(
            'trading_bot_errors_total',
            'Total errors',
            ['error_type', 'component']
        )

        self.strategy_errors = Counter(
            'trading_bot_strategy_errors_total',
            'Strategy execution errors',
            ['strategy', 'error_type']
        )

        # WebSocket Metrics
        self.websocket_connections = Gauge(
            'trading_bot_websocket_connections',
            'Active WebSocket connections'
        )

        self.websocket_messages = Counter(
            'trading_bot_websocket_messages_total',
            'WebSocket messages received',
            ['message_type']
        )

        self.websocket_reconnects = Counter(
            'trading_bot_websocket_reconnects_total',
            'WebSocket reconnection attempts'
        )

        # Initialize system monitoring
        self.start_time = time.time()
        self.monitoring_thread = None
        self.stop_monitoring = threading.Event()

        logger.info("Trading metrics initialized")

    def start_monitoring(self):
        """Start the monitoring thread"""
        if settings.enable_prometheus_metrics:
            # Start Prometheus metrics server
            start_http_server(settings.prometheus_port)
            logger.info(f"Prometheus metrics server started on port {settings.prometheus_port}")

        # Start system monitoring thread
        self.monitoring_thread = Thread(target=self._monitor_system, daemon=True)
        self.monitoring_thread.start()
        logger.info("System monitoring started")

    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self.stop_monitoring.set()
        if self.monitoring_thread:
            self.monitoring_thread.join()
        logger.info("System monitoring stopped")

    def _monitor_system(self):
        """Monitor system metrics in background thread"""
        while not self.stop_monitoring.is_set():
            try:
                # Update system metrics
                self.system_cpu_usage.set(psutil.cpu_percent())
                self.system_memory_usage.set(psutil.virtual_memory().used)
                self.system_uptime.set(time.time() - self.start_time)

                # Sleep for monitoring interval
                self.stop_monitoring.wait(30)  # Update every 30 seconds

            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
                self.stop_monitoring.wait(60)  # Wait longer on error

    def record_trade(self, side: str, symbol: str, strategy: str, status: str,
                    pnl: Optional[float] = None, size: Optional[float] = None):
        """Record a trade execution"""
        self.trades_total.labels(
            side=side,
            symbol=symbol,
            strategy=strategy,
            status=status
        ).inc()

        if pnl is not None:
            self.trade_pnl.labels(symbol=symbol, strategy=strategy).observe(pnl)

        if size is not None:
            self.position_size.labels(symbol=symbol).observe(size)

        logger.debug(f"Recorded trade: {side} {symbol} {strategy} {status}")

    def record_signal(self, signal_type: str, strategy: str, symbol: str, strength: float):
        """Record a trading signal"""
        self.signals_generated.labels(
            signal_type=signal_type,
            strategy=strategy,
            symbol=symbol
        ).inc()

        self.signal_strength.labels(
            signal_type=signal_type,
            strategy=strategy
        ).observe(strength)

        logger.debug(f"Recorded signal: {signal_type} {strategy} {symbol} strength={strength}")

    def record_api_call(self, endpoint: str, method: str, duration: float, status: str):
        """Record an API call"""
        self.api_requests_total.labels(
            endpoint=endpoint,
            method=method,
            status=status
        ).inc()

        self.api_request_duration.labels(
            endpoint=endpoint,
            method=method
        ).observe(duration)

    def record_api_error(self, endpoint: str, error_type: str):
        """Record an API error"""
        self.api_errors.labels(
            endpoint=endpoint,
            error_type=error_type
        ).inc()

    def record_rate_limit_hit(self):
        """Record a rate limit hit"""
        self.rate_limit_hits.inc()

    def update_portfolio_metrics(self, portfolio_value: float, unrealized_pnl: float,
                                daily_pnl: float, drawdown: float):
        """Update portfolio performance metrics"""
        self.portfolio_value.set(portfolio_value)
        self.unrealized_pnl.set(unrealized_pnl)
        self.daily_pnl.set(daily_pnl)
        self.drawdown.set(drawdown)

    def update_risk_metrics(self, risk_level: int, max_drawdown: float,
                           position_count: int, total_exposure: float):
        """Update risk metrics"""
        self.risk_level.set(risk_level)
        self.max_drawdown.set(max_drawdown)
        self.position_count.set(position_count)
        self.total_exposure.set(total_exposure)

    def update_win_rate(self, strategy: str, timeframe: str, win_rate: float):
        """Update win rate for a strategy"""
        self.win_rate.labels(strategy=strategy, timeframe=timeframe).set(win_rate)

    def record_error(self, error_type: str, component: str):
        """Record an error"""
        self.errors_total.labels(
            error_type=error_type,
            component=component
        ).inc()

    def record_strategy_error(self, strategy: str, error_type: str):
        """Record a strategy error"""
        self.strategy_errors.labels(
            strategy=strategy,
            error_type=error_type
        ).inc()

    def update_websocket_metrics(self, connections: int, message_type: Optional[str] = None,
                                reconnect: bool = False):
        """Update WebSocket metrics"""
        self.websocket_connections.set(connections)

        if message_type:
            self.websocket_messages.labels(message_type=message_type).inc()

        if reconnect:
            self.websocket_reconnects.inc()

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current metrics"""
        try:
            return {
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": time.time() - self.start_time,
                "portfolio": {
                    "value": self.portfolio_value._value._value,
                    "unrealized_pnl": self.unrealized_pnl._value._value,
                    "daily_pnl": self.daily_pnl._value._value,
                    "drawdown": self.drawdown._value._value
                },
                "risk": {
                    "level": self.risk_level._value._value,
                    "max_drawdown": self.max_drawdown._value._value,
                    "position_count": self.position_count._value._value,
                    "total_exposure": self.total_exposure._value._value
                },
                "system": {
                    "cpu_usage": self.system_cpu_usage._value._value,
                    "memory_usage": self.system_memory_usage._value._value
                },
                "trading": {
                    "total_trades": sum(metric._value._value for metric in self.trades_total._metrics.values()),
                    "total_signals": sum(metric._value._value for metric in self.signals_generated._metrics.values()),
                    "api_requests": sum(metric._value._value for metric in self.api_requests_total._metrics.values()),
                    "errors": sum(metric._value._value for metric in self.errors_total._metrics.values())
                }
            }
        except Exception as e:
            logger.error(f"Error getting metrics summary: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}


# Global metrics instance
trading_metrics = TradingMetrics()


class HealthChecker:
    """
    Health check system for monitoring bot status

    Provides:
    - Component health monitoring
    - Dependency checks
    - Performance thresholds
    - Alert generation
    """

    def __init__(self):
        self.checks = {}
        self.last_check_time = None
        self.health_status = "unknown"

    def add_check(self, name: str, check_func, critical: bool = False):
        """Add a health check"""
        self.checks[name] = {
            "func": check_func,
            "critical": critical,
            "last_result": None,
            "last_run": None
        }

    def run_health_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "checks": {}
        }

        critical_failed = False

        for name, check in self.checks.items():
            try:
                start_time = time.time()
                result = check["func"]()
                duration = time.time() - start_time

                check_result = {
                    "status": "healthy" if result else "unhealthy",
                    "duration_ms": duration * 1000,
                    "critical": check["critical"],
                    "details": result if isinstance(result, dict) else {"result": result}
                }

                if not result and check["critical"]:
                    critical_failed = True

                check["last_result"] = result
                check["last_run"] = datetime.now()

            except Exception as e:
                check_result = {
                    "status": "error",
                    "error": str(e),
                    "critical": check["critical"]
                }

                if check["critical"]:
                    critical_failed = True

            results["checks"][name] = check_result

        # Determine overall status
        if critical_failed:
            results["overall_status"] = "critical"
        elif any(check["status"] != "healthy" for check in results["checks"].values()):
            results["overall_status"] = "degraded"

        self.health_status = results["overall_status"]
        self.last_check_time = datetime.now()

        return results

    def get_health_status(self) -> str:
        """Get current health status"""
        return self.health_status


# Global health checker instance
health_checker = HealthChecker()


# Export main objects
__all__ = [
    "trading_metrics",
    "health_checker",
    "TradingMetrics",
    "HealthChecker"
]