"""
Main Trading Bot Application for Delta Exchange India

This is the main entry point for the Delta Exchange trading bot.
It orchestrates all components including:
- API client initialization
- Strategy management
- Risk management
- Monitoring and logging
- Error handling and recovery
"""

import asyncio
import signal
import sys
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor

from src.config import settings
from src.api import DeltaExchangeClient
from src.strategies import SMACrossoverStrategy, RSIStrategy, BaseStrategy
from src.utils import RiskManager, trading_logger, log_error, log_system
from src.database import db_manager
from src.monitoring.metrics import trading_metrics, health_checker
from src.utils.logger import logger


class TradingBot:
    """
    Main Trading Bot Application

    Coordinates all trading bot components:
    - Strategy execution
    - Risk management
    - Position monitoring
    - Performance tracking
    - Error handling
    """

    def __init__(self):
        self.client: Optional[DeltaExchangeClient] = None
        self.risk_manager: Optional[RiskManager] = None
        self.strategies: Dict[str, BaseStrategy] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Bot state
        self.running = False
        self.shutdown_event = threading.Event()
        self.last_health_check = None
        self.error_count = 0
        self.start_time = datetime.now()

        # Performance tracking
        self.iteration_count = 0
        self.total_trades = 0
        self.total_pnl = 0.0

        logger.info("Trading Bot initialized")

    def initialize(self) -> bool:
        """Initialize all bot components"""
        try:
            logger.info("Initializing Trading Bot components...")

            # Initialize API client
            self.client = DeltaExchangeClient()

            # Test API connection
            health_status = self.client.health_check()
            if health_status.get('status') != 'healthy':
                raise Exception(f"API health check failed: {health_status}")

            logger.info("✅ API client initialized and healthy")

            # Initialize risk manager
            self.risk_manager = RiskManager(self.client)
            self.risk_manager.initialize_daily_tracking()

            logger.info("✅ Risk manager initialized")

            # Initialize strategies
            self._initialize_strategies()

            logger.info("✅ Strategies initialized")

            # Initialize monitoring
            self._initialize_monitoring()

            logger.info("✅ Monitoring initialized")

            # Setup health checks
            self._setup_health_checks()

            logger.info("✅ Health checks configured")

            # Log system startup
            log_system("bot_started", {
                "strategies": list(self.strategies.keys()),
                "symbols": [s.symbol for s in self.strategies.values()],
                "risk_management_enabled": settings.enable_risk_management
            })

            logger.info("🚀 Trading Bot initialization complete")
            return True

        except Exception as e:
            log_error("initialization_error", f"Failed to initialize trading bot: {e}", exception=e)
            return False

    def _initialize_strategies(self):
        """Initialize trading strategies"""
        try:
            # Get available products to find product IDs
            products = self.client.get_products()
            symbol_to_product = {p.get('symbol'): p.get('id') for p in products}

            # Default symbol from settings
            default_symbol = settings.default_symbol
            if default_symbol not in symbol_to_product:
                raise Exception(f"Symbol {default_symbol} not found in available products")

            product_id = symbol_to_product[default_symbol]

            # Initialize strategy based on settings
            strategy_name = settings.strategy

            if strategy_name == "sma_crossover":
                strategy = SMACrossoverStrategy(self.client, product_id, default_symbol)
            elif strategy_name == "rsi_oversold_overbought":
                strategy = RSIStrategy(self.client, product_id, default_symbol)
            else:
                # Default to SMA crossover
                strategy = SMACrossoverStrategy(self.client, product_id, default_symbol)
                logger.warning(f"Unknown strategy '{strategy_name}', using SMA crossover")

            strategy.initialize()
            self.strategies[f"{strategy_name}_{default_symbol}"] = strategy

            logger.info(f"Strategy initialized: {strategy_name} for {default_symbol}")

        except Exception as e:
            log_error("strategy_initialization_error", f"Failed to initialize strategies: {e}", exception=e)
            raise

    def _initialize_monitoring(self):
        """Initialize monitoring and metrics"""
        try:
            # Start metrics collection
            trading_metrics.start_monitoring()

            # Initialize performance tracking
            self._track_initial_metrics()

            logger.info("Monitoring systems started")

        except Exception as e:
            log_error("monitoring_initialization_error", f"Failed to initialize monitoring: {e}", exception=e)
            raise

    def _setup_health_checks(self):
        """Setup health check functions"""
        def check_api_connection():
            try:
                result = self.client.health_check()
                return result.get('status') == 'healthy'
            except:
                return False

        def check_database_connection():
            try:
                stats = db_manager.get_database_stats()
                return isinstance(stats, dict)
            except:
                return False

        def check_risk_manager():
            try:
                risk_metrics = self.risk_manager.assess_portfolio_risk()
                return risk_metrics is not None
            except:
                return False

        def check_strategy_health():
            try:
                for strategy in self.strategies.values():
                    if strategy.state.consecutive_losses > 5:
                        return False
                return True
            except:
                return False

        # Add health checks
        health_checker.add_check("api_connection", check_api_connection, critical=True)
        health_checker.add_check("database_connection", check_database_connection, critical=True)
        health_checker.add_check("risk_manager", check_risk_manager, critical=True)
        health_checker.add_check("strategy_health", check_strategy_health, critical=False)

    def _track_initial_metrics(self):
        """Track initial metrics"""
        try:
            # Get account summary
            account_summary = self.client.get_account_summary()

            # Update portfolio metrics
            total_balance = account_summary.get('summary', {}).get('total_balance', 0)
            unrealized_pnl = account_summary.get('summary', {}).get('total_unrealized_pnl', 0)

            trading_metrics.update_portfolio_metrics(
                portfolio_value=total_balance,
                unrealized_pnl=unrealized_pnl,
                daily_pnl=0.0,
                drawdown=0.0
            )

            # Update risk metrics
            risk_metrics = self.risk_manager.assess_portfolio_risk()
            risk_level_map = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            risk_level_num = risk_level_map.get(risk_metrics.risk_level.value, 1)

            trading_metrics.update_risk_metrics(
                risk_level=risk_level_num,
                max_drawdown=risk_metrics.max_drawdown,
                position_count=len(account_summary.get('positions', [])),
                total_exposure=risk_metrics.total_exposure
            )

        except Exception as e:
            logger.warning(f"Failed to track initial metrics: {e}")

    async def run_main_loop(self):
        """Main trading loop"""
        logger.info("Starting main trading loop...")
        self.running = True

        try:
            while not self.shutdown_event.is_set():
                loop_start_time = time.time()

                try:
                    # Run one iteration of all strategies
                    await self._run_strategy_iteration()

                    # Update performance metrics
                    await self._update_performance_metrics()

                    # Run health checks periodically
                    if self._should_run_health_check():
                        await self._run_health_checks()

                    # Update iteration counter
                    self.iteration_count += 1

                    # Calculate loop duration
                    loop_duration = time.time() - loop_start_time

                    # Log performance
                    if self.iteration_count % 100 == 0:  # Every 100 iterations
                        logger.info(f"Completed {self.iteration_count} iterations. Loop time: {loop_duration:.2f}s")

                    # Sleep until next iteration (ensure minimum interval)
                    sleep_time = max(5.0 - loop_duration, 1.0)  # At least 1 second between iterations
                    await asyncio.sleep(sleep_time)

                except Exception as e:
                    self.error_count += 1
                    log_error("main_loop_error", f"Error in main loop iteration: {e}", exception=e)

                    # If too many consecutive errors, increase sleep time
                    if self.error_count > 5:
                        logger.warning("Multiple consecutive errors, sleeping longer...")
                        await asyncio.sleep(30)
                    else:
                        await asyncio.sleep(5)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
        except Exception as e:
            log_error("main_loop_fatal_error", f"Fatal error in main loop: {e}", exception=e)
        finally:
            await self._cleanup()

    async def _run_strategy_iteration(self):
        """Run one iteration of all strategies"""
        for strategy_name, strategy in self.strategies.items():
            try:
                # Generate signal
                signal = strategy.run_iteration()

                if signal:
                    # Record signal in metrics
                    trading_metrics.record_signal(
                        signal_type=signal.signal_type.value,
                        strategy=strategy_name,
                        symbol=strategy.symbol,
                        strength=signal.strength
                    )

                    # Save signal to database
                    signal_data = {
                        'strategy_name': strategy_name,
                        'symbol': strategy.symbol,
                        'signal_type': signal.signal_type.value,
                        'strength': signal.strength,
                        'confidence': signal.confidence,
                        'price': signal.price,
                        'reason': signal.reason,
                        'stop_loss': signal.stop_loss,
                        'take_profit': signal.take_profit,
                        'generated_at': signal.timestamp
                    }
                    db_signal = db_manager.save_signal(signal_data)

                    # Check if signal should be executed
                    if strategy.should_execute_signal(signal):
                        await self._execute_signal(strategy, signal, db_signal.id)

            except Exception as e:
                self.error_count += 1
                log_error("strategy_iteration_error",
                         f"Error in strategy {strategy_name} iteration: {e}",
                         context={"strategy": strategy_name},
                         exception=e)

                # Record strategy error in metrics
                trading_metrics.record_strategy_error(strategy_name, "iteration_error")

    async def _execute_signal(self, strategy: BaseStrategy, signal, signal_id: int):
        """Execute a trading signal"""
        try:
            # Get current account balance
            balances = self.client.get_balances()
            total_balance = sum(float(b.available_balance) for b in balances if b.available_balance)

            # Calculate position size
            position_size = self.risk_manager.calculate_position_size(
                signal, total_balance, signal.price
            )

            # Check risk management
            can_trade, reason = self.risk_manager.should_allow_new_position(
                signal, position_size, signal.price
            )

            if not can_trade:
                logger.warning(f"Trade blocked by risk management: {reason}")
                return

            # Execute the order
            result = strategy.execute_order(signal, position_size)

            if result:
                self.total_trades += 1

                # Record trade in metrics
                trading_metrics.record_trade(
                    side=signal.signal_type.value,
                    symbol=strategy.symbol,
                    strategy=strategy.__class__.__name__,
                    status="executed",
                    size=position_size
                )

                # Save trade to database
                trade_data = {
                    'trade_id': result.get('id'),
                    'order_id': result.get('id'),
                    'product_id': strategy.product_id,
                    'symbol': strategy.symbol,
                    'side': signal.signal_type.value,
                    'order_type': 'market',
                    'size': position_size,
                    'price': signal.price,
                    'strategy_name': strategy.__class__.__name__,
                    'signal_strength': signal.strength,
                    'signal_confidence': signal.confidence,
                    'executed_at': datetime.now()
                }
                db_manager.save_trade(trade_data)

                # Update signal execution
                db_manager.update_signal_execution(signal_id, {
                    'execution_price': signal.price,
                    'executed_at': datetime.now()
                })

                logger.info(f"✅ Trade executed: {signal.signal_type.value} {position_size} {strategy.symbol} @ {signal.price}")

            else:
                logger.error(f"❌ Failed to execute trade for {strategy.symbol}")

        except Exception as e:
            log_error("signal_execution_error",
                     f"Error executing signal: {e}",
                     context={"signal": signal.signal_type.value, "symbol": strategy.symbol},
                     exception=e)

    async def _update_performance_metrics(self):
        """Update performance metrics"""
        try:
            # Get account summary
            account_summary = self.client.get_account_summary()

            # Update portfolio metrics
            total_balance = account_summary.get('summary', {}).get('total_balance', 0)
            unrealized_pnl = account_summary.get('summary', {}).get('total_unrealized_pnl', 0)

            # Calculate daily P&L
            daily_pnl = self.risk_manager.daily_pnl

            trading_metrics.update_portfolio_metrics(
                portfolio_value=total_balance,
                unrealized_pnl=unrealized_pnl,
                daily_pnl=daily_pnl,
                drawdown=self.risk_manager.current_drawdown
            )

            # Update risk metrics
            risk_metrics = self.risk_manager.assess_portfolio_risk()
            risk_level_map = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            risk_level_num = risk_level_map.get(risk_metrics.risk_level.value, 1)

            trading_metrics.update_risk_metrics(
                risk_level=risk_level_num,
                max_drawdown=risk_metrics.max_drawdown,
                position_count=len(account_summary.get('positions', [])),
                total_exposure=risk_metrics.total_exposure
            )

        except Exception as e:
            logger.warning(f"Failed to update performance metrics: {e}")

    def _should_run_health_check(self) -> bool:
        """Check if health check should be run"""
        if not self.last_health_check:
            return True

        time_since_last = datetime.now() - self.last_health_check
        return time_since_last.total_seconds() > settings.health_check_interval

    async def _run_health_checks(self):
        """Run health checks"""
        try:
            health_results = health_checker.run_health_checks()
            self.last_health_check = datetime.now()

            # Log health status
            overall_status = health_results.get('overall_status', 'unknown')
            logger.info(f"Health check completed: {overall_status}")

            # Take action based on health status
            if overall_status == 'critical':
                logger.critical("Critical health issues detected!")
                # Could implement emergency shutdown here

            elif overall_status == 'degraded':
                logger.warning("System health is degraded")

            # Reset error count on successful health check
            if overall_status == 'healthy':
                self.error_count = 0

        except Exception as e:
            log_error("health_check_error", f"Error running health checks: {e}", exception=e)

    async def _cleanup(self):
        """Cleanup resources before shutdown"""
        logger.info("Cleaning up resources...")

        try:
            # Stop monitoring
            trading_metrics.stop_monitoring()

            # Close database connections
            db_manager.close_thread_session()

            # Close API client connections
            if self.client:
                # Close any open connections
                pass

            # Shutdown executor
            self.executor.shutdown(wait=True)

            # Log final statistics
            uptime = datetime.now() - self.start_time
            log_system("bot_stopped", {
                "uptime_seconds": uptime.total_seconds(),
                "total_iterations": self.iteration_count,
                "total_trades": self.total_trades,
                "error_count": self.error_count
            })

            logger.info("🛑 Trading Bot shutdown complete")

        except Exception as e:
            log_error("cleanup_error", f"Error during cleanup: {e}", exception=e)

    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutdown signal received...")
        self.running = False
        self.shutdown_event.set()

    def get_status(self) -> Dict[str, Any]:
        """Get current bot status"""
        uptime = datetime.now() - self.start_time

        return {
            "running": self.running,
            "uptime_seconds": uptime.total_seconds(),
            "uptime_formatted": f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds%3600)//60}m",
            "iteration_count": self.iteration_count,
            "total_trades": self.total_trades,
            "error_count": self.error_count,
            "strategies": len(self.strategies),
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "health_status": health_checker.get_health_status()
        }


# Global bot instance
bot = None


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    if bot:
        bot.shutdown()
    sys.exit(0)


async def main():
    """Main application entry point"""
    global bot

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and initialize bot
    bot = TradingBot()

    if not bot.initialize():
        logger.error("Failed to initialize trading bot")
        sys.exit(1)

    # Run main loop
    await bot.run_main_loop()


if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())