"""
Database Manager for Delta Exchange Trading Bot

This module provides comprehensive database management including:
- Connection management
- Session handling
- Data persistence
- Analytics queries
- Performance optimization
"""

import os
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from contextlib import contextmanager
import threading

from sqlalchemy import create_engine, func, and_, or_, desc, asc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool

from src.config import settings
from src.database.models import (
    Base, Trade, Position, StrategyPerformance, RiskEvent, Signal,
    BalanceSnapshot, SystemEvent, DailyStats
)
from src.utils.logger import trading_logger, logger


class DatabaseManager:
    """
    Comprehensive database management system

    Features:
    - Connection pooling
    - Session management
    - Data persistence
    - Analytics queries
    - Performance optimization
    - Error handling
    """

    def __init__(self):
        self.database_url = settings.get_database_url()
        self.engine = None
        self.SessionLocal = None
        self._local = threading.local()

        self.initialize_database()

    def initialize_database(self):
        """Initialize database connection and create tables"""
        try:
            # Create engine with connection pooling
            if self.database_url.startswith("sqlite"):
                # SQLite specific configuration
                self.engine = create_engine(
                    self.database_url,
                    poolclass=StaticPool,
                    connect_args={
                        "check_same_thread": False,
                        "timeout": 30
                    },
                    echo=settings.debug
                )
            else:
                # PostgreSQL/MySQL configuration
                self.engine = create_engine(
                    self.database_url,
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=30,
                    pool_recycle=1800,
                    echo=settings.debug
                )

            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            # Create all tables
            Base.metadata.create_all(bind=self.engine)

            logger.info(f"Database initialized: {self.database_url}")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    @contextmanager
    def get_session(self):
        """Get database session with automatic cleanup"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def get_thread_session(self) -> Session:
        """Get thread-local database session"""
        if not hasattr(self._local, 'session'):
            self._local.session = self.SessionLocal()
        return self._local.session

    def close_thread_session(self):
        """Close thread-local session"""
        if hasattr(self._local, 'session'):
            self._local.session.close()
            delattr(self._local, 'session')

    # ==================== TRADE OPERATIONS ====================

    def save_trade(self, trade_data: Dict[str, Any]) -> Trade:
        """Save a trade record"""
        with self.get_session() as session:
            trade = Trade(
                trade_id=trade_data.get('trade_id'),
                order_id=trade_data.get('order_id'),
                product_id=trade_data.get('product_id'),
                symbol=trade_data.get('symbol'),
                side=trade_data.get('side'),
                order_type=trade_data.get('order_type'),
                size=trade_data.get('size'),
                price=trade_data.get('price'),
                fee=trade_data.get('fee', 0.0),
                strategy_name=trade_data.get('strategy_name'),
                signal_strength=trade_data.get('signal_strength'),
                signal_confidence=trade_data.get('signal_confidence'),
                executed_at=trade_data.get('executed_at', datetime.now()),
                realized_pnl=trade_data.get('realized_pnl'),
                commission=trade_data.get('commission', 0.0),
                metadata=trade_data.get('metadata')
            )

            session.add(trade)
            session.flush()

            logger.info(f"Trade saved: {trade.symbol} {trade.side} {trade.size} @ {trade.price}")
            return trade

    def get_trades(self, symbol: Optional[str] = None, strategy: Optional[str] = None,
                  start_time: Optional[datetime] = None, end_time: Optional[datetime] = None,
                  limit: int = 100) -> List[Trade]:
        """Get trade records with filtering"""
        with self.get_session() as session:
            query = session.query(Trade)

            if symbol:
                query = query.filter(Trade.symbol == symbol)
            if strategy:
                query = query.filter(Trade.strategy_name == strategy)
            if start_time:
                query = query.filter(Trade.executed_at >= start_time)
            if end_time:
                query = query.filter(Trade.executed_at <= end_time)

            return query.order_by(desc(Trade.executed_at)).limit(limit).all()

    def get_trade_summary(self, period_days: int = 30) -> Dict[str, Any]:
        """Get trade summary statistics"""
        with self.get_session() as session:
            start_date = datetime.now() - timedelta(days=period_days)

            # Basic statistics
            total_trades = session.query(func.count(Trade.id)).filter(
                Trade.executed_at >= start_date
            ).scalar()

            buy_trades = session.query(func.count(Trade.id)).filter(
                and_(Trade.executed_at >= start_date, Trade.side == 'buy')
            ).scalar()

            sell_trades = session.query(func.count(Trade.id)).filter(
                and_(Trade.executed_at >= start_date, Trade.side == 'sell')
            ).scalar()

            # P&L statistics
            total_pnl = session.query(func.sum(Trade.realized_pnl)).filter(
                and_(Trade.executed_at >= start_date, Trade.realized_pnl.isnot(None))
            ).scalar() or 0.0

            total_fees = session.query(func.sum(Trade.fee)).filter(
                Trade.executed_at >= start_date
            ).scalar() or 0.0

            # Volume statistics
            total_volume = session.query(func.sum(Trade.size * Trade.price)).filter(
                Trade.executed_at >= start_date
            ).scalar() or 0.0

            return {
                "period_days": period_days,
                "total_trades": total_trades or 0,
                "buy_trades": buy_trades or 0,
                "sell_trades": sell_trades or 0,
                "total_pnl": total_pnl,
                "total_fees": total_fees,
                "net_pnl": total_pnl - total_fees,
                "total_volume": total_volume,
                "avg_trade_size": total_volume / max(total_trades, 1)
            }

    # ==================== POSITION OPERATIONS ====================

    def save_position(self, position_data: Dict[str, Any]) -> Position:
        """Save a position record"""
        with self.get_session() as session:
            position = Position(
                product_id=position_data.get('product_id'),
                symbol=position_data.get('symbol'),
                size=position_data.get('size'),
                entry_price=position_data.get('entry_price'),
                current_price=position_data.get('current_price'),
                mark_price=position_data.get('mark_price'),
                unrealized_pnl=position_data.get('unrealized_pnl', 0.0),
                realized_pnl=position_data.get('realized_pnl', 0.0),
                stop_loss_price=position_data.get('stop_loss_price'),
                take_profit_price=position_data.get('take_profit_price'),
                leverage=position_data.get('leverage', 1.0),
                margin=position_data.get('margin'),
                strategy_name=position_data.get('strategy_name'),
                status=position_data.get('status', 'open'),
                opened_at=position_data.get('opened_at', datetime.now()),
                trade_id=position_data.get('trade_id'),
                metadata=position_data.get('metadata')
            )

            session.add(position)
            session.flush()

            logger.info(f"Position saved: {position.symbol} {position.size} @ {position.entry_price}")
            return position

    def update_position(self, position_id: int, updates: Dict[str, Any]) -> Optional[Position]:
        """Update a position record"""
        with self.get_session() as session:
            position = session.query(Position).filter(Position.id == position_id).first()

            if position:
                for key, value in updates.items():
                    if hasattr(position, key):
                        setattr(position, key, value)

                position.updated_at = datetime.now()
                session.flush()

                logger.info(f"Position updated: {position.symbol} (ID: {position_id})")
                return position

            return None

    def close_position(self, position_id: int, close_price: float, realized_pnl: float) -> bool:
        """Close a position"""
        with self.get_session() as session:
            position = session.query(Position).filter(Position.id == position_id).first()

            if position:
                position.status = 'closed'
                position.current_price = close_price
                position.realized_pnl = realized_pnl
                position.closed_at = datetime.now()
                position.updated_at = datetime.now()

                logger.info(f"Position closed: {position.symbol} PnL: {realized_pnl}")
                return True

            return False

    def get_open_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get open positions"""
        with self.get_session() as session:
            query = session.query(Position).filter(Position.status == 'open')

            if symbol:
                query = query.filter(Position.symbol == symbol)

            return query.all()

    # ==================== SIGNAL OPERATIONS ====================

    def save_signal(self, signal_data: Dict[str, Any]) -> Signal:
        """Save a trading signal"""
        with self.get_session() as session:
            signal = Signal(
                strategy_name=signal_data.get('strategy_name'),
                symbol=signal_data.get('symbol'),
                signal_type=signal_data.get('signal_type'),
                strength=signal_data.get('strength'),
                confidence=signal_data.get('confidence'),
                price=signal_data.get('price'),
                reason=signal_data.get('reason'),
                stop_loss=signal_data.get('stop_loss'),
                take_profit=signal_data.get('take_profit'),
                position_size=signal_data.get('position_size'),
                generated_at=signal_data.get('generated_at', datetime.now()),
                indicators=signal_data.get('indicators'),
                market_conditions=signal_data.get('market_conditions'),
                metadata=signal_data.get('metadata')
            )

            session.add(signal)
            session.flush()

            logger.debug(f"Signal saved: {signal.strategy_name} {signal.signal_type} {signal.symbol}")
            return signal

    def update_signal_execution(self, signal_id: int, execution_data: Dict[str, Any]) -> bool:
        """Update signal with execution data"""
        with self.get_session() as session:
            signal = session.query(Signal).filter(Signal.id == signal_id).first()

            if signal:
                signal.executed = True
                signal.execution_price = execution_data.get('execution_price')
                signal.executed_at = execution_data.get('executed_at', datetime.now())

                if signal.generated_at and signal.executed_at:
                    signal.execution_delay = (signal.executed_at - signal.generated_at).total_seconds()

                return True

            return False

    # ==================== ANALYTICS OPERATIONS ====================

    def save_strategy_performance(self, performance_data: Dict[str, Any]) -> StrategyPerformance:
        """Save strategy performance metrics"""
        with self.get_session() as session:
            # Check if record already exists
            existing = session.query(StrategyPerformance).filter(
                and_(
                    StrategyPerformance.strategy_name == performance_data.get('strategy_name'),
                    StrategyPerformance.symbol == performance_data.get('symbol'),
                    StrategyPerformance.timeframe == performance_data.get('timeframe'),
                    StrategyPerformance.period_start == performance_data.get('period_start')
                )
            ).first()

            if existing:
                # Update existing record
                for key, value in performance_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.updated_at = datetime.now()
                return existing
            else:
                # Create new record
                performance = StrategyPerformance(**performance_data)
                session.add(performance)
                session.flush()
                return performance

    def get_strategy_performance(self, strategy_name: str, symbol: Optional[str] = None,
                               days: int = 30) -> List[StrategyPerformance]:
        """Get strategy performance records"""
        with self.get_session() as session:
            start_date = datetime.now() - timedelta(days=days)

            query = session.query(StrategyPerformance).filter(
                and_(
                    StrategyPerformance.strategy_name == strategy_name,
                    StrategyPerformance.period_start >= start_date
                )
            )

            if symbol:
                query = query.filter(StrategyPerformance.symbol == symbol)

            return query.order_by(desc(StrategyPerformance.period_start)).all()

    def save_risk_event(self, event_data: Dict[str, Any]) -> RiskEvent:
        """Save a risk event"""
        with self.get_session() as session:
            event = RiskEvent(
                event_type=event_data.get('event_type'),
                severity=event_data.get('severity'),
                description=event_data.get('description'),
                symbol=event_data.get('symbol'),
                strategy_name=event_data.get('strategy_name'),
                position_id=event_data.get('position_id'),
                portfolio_value=event_data.get('portfolio_value'),
                total_exposure=event_data.get('total_exposure'),
                drawdown_percent=event_data.get('drawdown_percent'),
                risk_level=event_data.get('risk_level'),
                action_taken=event_data.get('action_taken'),
                occurred_at=event_data.get('occurred_at', datetime.now()),
                metadata=event_data.get('metadata')
            )

            session.add(event)
            session.flush()

            logger.warning(f"Risk event saved: {event.event_type} - {event.severity}")
            return event

    def save_balance_snapshot(self, balance_data: Dict[str, Any]) -> BalanceSnapshot:
        """Save a balance snapshot"""
        with self.get_session() as session:
            snapshot = BalanceSnapshot(
                total_balance=balance_data.get('total_balance'),
                available_balance=balance_data.get('available_balance'),
                used_balance=balance_data.get('used_balance'),
                asset_balances=balance_data.get('asset_balances'),
                daily_pnl=balance_data.get('daily_pnl', 0.0),
                total_pnl=balance_data.get('total_pnl', 0.0),
                unrealized_pnl=balance_data.get('unrealized_pnl', 0.0),
                margin_used=balance_data.get('margin_used', 0.0),
                margin_available=balance_data.get('margin_available', 0.0),
                margin_ratio=balance_data.get('margin_ratio', 0.0),
                snapshot_at=balance_data.get('snapshot_at', datetime.now()),
                metadata=balance_data.get('metadata')
            )

            session.add(snapshot)
            session.flush()

            return snapshot

    def get_portfolio_history(self, days: int = 30) -> List[BalanceSnapshot]:
        """Get portfolio value history"""
        with self.get_session() as session:
            start_date = datetime.now() - timedelta(days=days)

            return session.query(BalanceSnapshot).filter(
                BalanceSnapshot.snapshot_at >= start_date
            ).order_by(asc(BalanceSnapshot.snapshot_at)).all()

    def calculate_daily_stats(self, date: datetime) -> DailyStats:
        """Calculate and save daily statistics"""
        with self.get_session() as session:
            # Define date range
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)

            # Calculate trade statistics
            trades = session.query(Trade).filter(
                and_(
                    Trade.executed_at >= start_of_day,
                    Trade.executed_at < end_of_day
                )
            ).all()

            total_trades = len(trades)
            winning_trades = sum(1 for t in trades if t.realized_pnl and t.realized_pnl > 0)
            losing_trades = sum(1 for t in trades if t.realized_pnl and t.realized_pnl < 0)
            daily_pnl = sum(t.realized_pnl for t in trades if t.realized_pnl) or 0.0
            total_volume = sum(t.size * t.price for t in trades)

            # Get balance snapshots
            balance_start = session.query(BalanceSnapshot).filter(
                BalanceSnapshot.snapshot_at >= start_of_day
            ).order_by(asc(BalanceSnapshot.snapshot_at)).first()

            balance_end = session.query(BalanceSnapshot).filter(
                BalanceSnapshot.snapshot_at < end_of_day
            ).order_by(desc(BalanceSnapshot.snapshot_at)).first()

            # Check if daily stats already exist
            existing = session.query(DailyStats).filter(
                DailyStats.date == start_of_day
            ).first()

            stats_data = {
                'date': start_of_day,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'daily_pnl': daily_pnl,
                'total_volume': total_volume,
                'avg_trade_size': total_volume / max(total_trades, 1),
                'starting_balance': balance_start.total_balance if balance_start else None,
                'ending_balance': balance_end.total_balance if balance_end else None
            }

            if existing:
                for key, value in stats_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.updated_at = datetime.now()
                return existing
            else:
                daily_stats = DailyStats(**stats_data)
                session.add(daily_stats)
                session.flush()
                return daily_stats

    def cleanup_old_data(self, days_to_keep: int = 365):
        """Clean up old data to manage database size"""
        with self.get_session() as session:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            # Clean up old signals
            deleted_signals = session.query(Signal).filter(
                Signal.generated_at < cutoff_date
            ).delete()

            # Clean up old balance snapshots (keep daily snapshots)
            deleted_snapshots = session.query(BalanceSnapshot).filter(
                and_(
                    BalanceSnapshot.snapshot_at < cutoff_date,
                    func.extract('hour', BalanceSnapshot.snapshot_at) != 0
                )
            ).delete()

            # Clean up resolved old system events
            deleted_events = session.query(SystemEvent).filter(
                and_(
                    SystemEvent.occurred_at < cutoff_date,
                    SystemEvent.resolved == True
                )
            ).delete()

            logger.info(f"Cleaned up old data: {deleted_signals} signals, {deleted_snapshots} snapshots, {deleted_events} events")

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        with self.get_session() as session:
            stats = {}

            # Count records in each table
            tables = [Trade, Position, Signal, StrategyPerformance, RiskEvent,
                     BalanceSnapshot, SystemEvent, DailyStats]

            for table in tables:
                count = session.query(func.count(table.id)).scalar()
                stats[table.__tablename__] = count

            # Database size (for SQLite)
            if self.database_url.startswith("sqlite"):
                db_path = self.database_url.replace("sqlite:///", "")
                if os.path.exists(db_path):
                    stats['database_size_mb'] = os.path.getsize(db_path) / (1024 * 1024)

            return stats


# Global database manager instance
db_manager = DatabaseManager()


# Export main objects
__all__ = [
    "db_manager",
    "DatabaseManager"
]