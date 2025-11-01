"""
Advanced Logging System for Delta Exchange Trading Bot

This module provides comprehensive logging capabilities with:
- Multiple log levels and outputs
- Structured logging with JSON format
- Performance monitoring
- Trade execution logging
- Error tracking and alerting
"""

import sys
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from loguru import logger
from src.config import settings


class TradingLogger:
    """
    Advanced logging system for trading operations

    Features:
    - Structured JSON logging
    - Multiple output destinations
    - Performance metrics
    - Trade execution tracking
    - Error categorization
    - Log rotation and retention
    """

    def __init__(self):
        self.setup_logging()
        self.trade_counter = 0
        self.error_counter = 0
        self.start_time = datetime.now()

    def setup_logging(self):
        """Configure loguru logger with multiple outputs"""

        # Remove default logger
        logger.remove()

        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Console logging with colors
        logger.add(
            sys.stdout,
            level=settings.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True,
            backtrace=True,
            diagnose=True
        )

        # Main application log file
        logger.add(
            "logs/trading_bot.log",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="100 MB",
            retention="30 days",
            compression="zip",
            backtrace=True,
            diagnose=True
        )

        # Error log file
        logger.add(
            "logs/errors.log",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="50 MB",
            retention="60 days",
            compression="zip",
            backtrace=True,
            diagnose=True
        )

        # Trade execution log (structured JSON)
        logger.add(
            "logs/trades.jsonl",
            level="INFO",
            format="{message}",
            filter=lambda record: "trade_execution" in record["extra"],
            rotation="50 MB",
            retention="180 days",
            compression="zip"
        )

        # Performance metrics log
        logger.add(
            "logs/performance.jsonl",
            level="INFO",
            format="{message}",
            filter=lambda record: "performance" in record["extra"],
            rotation="50 MB",
            retention="90 days",
            compression="zip"
        )

        # Risk events log
        logger.add(
            "logs/risk_events.log",
            level="WARNING",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
            filter=lambda record: "risk_event" in record["extra"],
            rotation="50 MB",
            retention="365 days",
            compression="zip"
        )

        logger.info("Logging system initialized")

    def log_trade_execution(self, trade_data: Dict[str, Any]):
        """Log trade execution with structured data"""
        self.trade_counter += 1

        trade_log = {
            "timestamp": datetime.now().isoformat(),
            "trade_id": self.trade_counter,
            "type": "trade_execution",
            **trade_data
        }

        logger.bind(trade_execution=True).info(json.dumps(trade_log))
        logger.info(f"Trade executed: {trade_data.get('side', 'unknown')} {trade_data.get('size', 0)} {trade_data.get('symbol', 'unknown')} at {trade_data.get('price', 0)}")

    def log_signal_generated(self, signal_data: Dict[str, Any]):
        """Log trading signal generation"""
        signal_log = {
            "timestamp": datetime.now().isoformat(),
            "type": "signal_generated",
            **signal_data
        }

        logger.info(f"Signal generated: {signal_data.get('signal_type', 'unknown')} for {signal_data.get('symbol', 'unknown')} - Strength: {signal_data.get('strength', 0):.2f}")
        logger.bind(signal=True).debug(json.dumps(signal_log))

    def log_risk_event(self, event_type: str, details: Dict[str, Any]):
        """Log risk management events"""
        risk_log = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "type": "risk_event",
            **details
        }

        logger.bind(risk_event=True).warning(f"Risk Event: {event_type} - {details}")

    def log_performance_metric(self, metric_name: str, value: float, details: Optional[Dict] = None):
        """Log performance metrics"""
        perf_log = {
            "timestamp": datetime.now().isoformat(),
            "type": "performance_metric",
            "metric": metric_name,
            "value": value,
            "details": details or {}
        }

        logger.bind(performance=True).info(json.dumps(perf_log))
        logger.debug(f"Performance metric: {metric_name} = {value}")

    def log_api_call(self, endpoint: str, method: str, response_time: float, success: bool, details: Optional[Dict] = None):
        """Log API calls with performance data"""
        api_log = {
            "timestamp": datetime.now().isoformat(),
            "type": "api_call",
            "endpoint": endpoint,
            "method": method,
            "response_time_ms": response_time * 1000,
            "success": success,
            "details": details or {}
        }

        level = "INFO" if success else "ERROR"
        status = "SUCCESS" if success else "FAILED"

        logger.log(level, f"API Call: {method} {endpoint} - {status} ({response_time*1000:.1f}ms)")
        logger.bind(api_call=True).debug(json.dumps(api_log))

    def log_strategy_update(self, strategy_name: str, symbol: str, state: Dict[str, Any]):
        """Log strategy state updates"""
        strategy_log = {
            "timestamp": datetime.now().isoformat(),
            "type": "strategy_update",
            "strategy": strategy_name,
            "symbol": symbol,
            "state": state
        }

        logger.info(f"Strategy update: {strategy_name} for {symbol}")
        logger.bind(strategy=True).debug(json.dumps(strategy_log))

    def log_error(self, error_type: str, error_message: str, context: Optional[Dict] = None, exception: Optional[Exception] = None):
        """Log errors with categorization"""
        self.error_counter += 1

        error_log = {
            "timestamp": datetime.now().isoformat(),
            "error_id": self.error_counter,
            "type": "error",
            "error_type": error_type,
            "message": error_message,
            "context": context or {},
            "exception": str(exception) if exception else None
        }

        if exception:
            logger.exception(f"Error [{error_type}]: {error_message}")
        else:
            logger.error(f"Error [{error_type}]: {error_message}")

        logger.bind(error=True).error(json.dumps(error_log))

    def log_system_status(self, status: str, details: Dict[str, Any]):
        """Log system status changes"""
        status_log = {
            "timestamp": datetime.now().isoformat(),
            "type": "system_status",
            "status": status,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "trade_count": self.trade_counter,
            "error_count": self.error_counter,
            **details
        }

        logger.info(f"System status: {status}")
        logger.bind(system=True).info(json.dumps(status_log))

    def log_position_update(self, position_data: Dict[str, Any]):
        """Log position updates"""
        position_log = {
            "timestamp": datetime.now().isoformat(),
            "type": "position_update",
            **position_data
        }

        logger.info(f"Position update: {position_data.get('symbol', 'unknown')} - Size: {position_data.get('size', 0)}, PnL: {position_data.get('unrealized_pnl', 0)}")
        logger.bind(position=True).debug(json.dumps(position_log))

    def log_balance_update(self, balance_data: Dict[str, Any]):
        """Log balance updates"""
        balance_log = {
            "timestamp": datetime.now().isoformat(),
            "type": "balance_update",
            **balance_data
        }

        logger.info(f"Balance update: Total balance: {balance_data.get('total_balance', 0)}")
        logger.bind(balance=True).debug(json.dumps(balance_log))

    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        uptime = (datetime.now() - self.start_time).total_seconds()

        return {
            "uptime_seconds": uptime,
            "uptime_formatted": f"{uptime//3600:.0f}h {(uptime%3600)//60:.0f}m {uptime%60:.0f}s",
            "total_trades": self.trade_counter,
            "total_errors": self.error_counter,
            "error_rate": self.error_counter / max(uptime / 3600, 1),  # errors per hour
            "trade_rate": self.trade_counter / max(uptime / 3600, 1),  # trades per hour
            "start_time": self.start_time.isoformat(),
            "current_time": datetime.now().isoformat()
        }


# Global logger instance
trading_logger = TradingLogger()


# Convenience functions for easy access
def log_trade(trade_data: Dict[str, Any]):
    """Log trade execution"""
    trading_logger.log_trade_execution(trade_data)


def log_signal(signal_data: Dict[str, Any]):
    """Log signal generation"""
    trading_logger.log_signal_generated(signal_data)


def log_risk(event_type: str, details: Dict[str, Any]):
    """Log risk event"""
    trading_logger.log_risk_event(event_type, details)


def log_performance(metric_name: str, value: float, details: Optional[Dict] = None):
    """Log performance metric"""
    trading_logger.log_performance_metric(metric_name, value, details)


def log_api(endpoint: str, method: str, response_time: float, success: bool, details: Optional[Dict] = None):
    """Log API call"""
    trading_logger.log_api_call(endpoint, method, response_time, success, details)


def log_error(error_type: str, error_message: str, context: Optional[Dict] = None, exception: Optional[Exception] = None):
    """Log error"""
    trading_logger.log_error(error_type, error_message, context, exception)


def log_system(status: str, details: Dict[str, Any]):
    """Log system status"""
    trading_logger.log_system_status(status, details)


# Export logger for direct use
__all__ = [
    "trading_logger",
    "log_trade",
    "log_signal",
    "log_risk",
    "log_performance",
    "log_api",
    "log_error",
    "log_system",
    "logger"
]