"""
Database Models for Delta Exchange Trading Bot

This module defines SQLAlchemy models for:
- Trade history tracking
- Position management
- Performance analytics
- Risk events
- Strategy performance
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, JSON,
    Index, ForeignKey, UniqueConstraint, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Trade(Base):
    """Trade execution records"""
    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Trade identification
    trade_id = Column(String(50), unique=True, nullable=False)
    order_id = Column(String(50), nullable=False)
    product_id = Column(Integer, nullable=False)
    symbol = Column(String(20), nullable=False)

    # Trade details
    side = Column(String(10), nullable=False)  # 'buy' or 'sell'
    order_type = Column(String(20), nullable=False)
    size = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)

    # Strategy information
    strategy_name = Column(String(50), nullable=False)
    signal_strength = Column(Float)
    signal_confidence = Column(Float)

    # Timestamps
    executed_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # P&L tracking
    realized_pnl = Column(Float)
    commission = Column(Float, default=0.0)

    # Additional metadata
    extra_data = Column(JSON)

    # Relationships
    positions = relationship("Position", back_populates="trade")

    # Indexes
    __table_args__ = (
        Index('idx_trades_symbol_time', 'symbol', 'executed_at'),
        Index('idx_trades_strategy', 'strategy_name'),
        Index('idx_trades_product', 'product_id'),
        CheckConstraint('size > 0', name='check_positive_size'),
        CheckConstraint('price > 0', name='check_positive_price'),
        CheckConstraint("side IN ('buy', 'sell')", name='check_valid_side')
    )

    def __repr__(self):
        return f"<Trade(id={self.id}, symbol={self.symbol}, side={self.side}, size={self.size}, price={self.price})>"


class Position(Base):
    """Position tracking"""
    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Position identification
    product_id = Column(Integer, nullable=False)
    symbol = Column(String(20), nullable=False)

    # Position details
    size = Column(Float, nullable=False)  # Positive for long, negative for short
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float)
    mark_price = Column(Float)

    # P&L tracking
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)

    # Risk management
    stop_loss_price = Column(Float)
    take_profit_price = Column(Float)
    leverage = Column(Float, default=1.0)
    margin = Column(Float)

    # Strategy information
    strategy_name = Column(String(50), nullable=False)

    # Status
    status = Column(String(20), default='open')  # 'open', 'closed', 'liquidated'

    # Timestamps
    opened_at = Column(DateTime, nullable=False)
    closed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    trade_id = Column(Integer, ForeignKey('trades.id'))
    trade = relationship("Trade", back_populates="positions")

    # Additional metadata
    extra_data = Column(JSON)

    # Indexes
    __table_args__ = (
        Index('idx_positions_symbol_status', 'symbol', 'status'),
        Index('idx_positions_strategy', 'strategy_name'),
        Index('idx_positions_product', 'product_id'),
        CheckConstraint('size != 0', name='check_nonzero_size'),
        CheckConstraint('entry_price > 0', name='check_positive_entry_price'),
        CheckConstraint("status IN ('open', 'closed', 'liquidated')", name='check_valid_status')
    )

    def __repr__(self):
        return f"<Position(id={self.id}, symbol={self.symbol}, size={self.size}, status={self.status})>"


class StrategyPerformance(Base):
    """Strategy performance tracking"""
    __tablename__ = 'strategy_performance'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Strategy identification
    strategy_name = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)  # '1m', '5m', '1h', etc.

    # Performance metrics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)

    # P&L metrics
    total_pnl = Column(Float, default=0.0)
    gross_profit = Column(Float, default=0.0)
    gross_loss = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)

    # Risk metrics
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    sortino_ratio = Column(Float, default=0.0)
    calmar_ratio = Column(Float, default=0.0)

    # Trade statistics
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    largest_win = Column(Float, default=0.0)
    largest_loss = Column(Float, default=0.0)
    avg_trade_duration = Column(Float, default=0.0)  # in minutes

    # Signal statistics
    total_signals = Column(Integer, default=0)
    executed_signals = Column(Integer, default=0)
    signal_efficiency = Column(Float, default=0.0)

    # Time tracking
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Additional metrics
    extra_data = Column(JSON)

    # Indexes
    __table_args__ = (
        Index('idx_strategy_perf_name_symbol', 'strategy_name', 'symbol'),
        Index('idx_strategy_perf_timeframe', 'timeframe'),
        Index('idx_strategy_perf_period', 'period_start', 'period_end'),
        UniqueConstraint('strategy_name', 'symbol', 'timeframe', 'period_start',
                        name='uq_strategy_period')
    )

    def __repr__(self):
        return f"<StrategyPerformance(strategy={self.strategy_name}, symbol={self.symbol}, win_rate={self.win_rate:.2f})>"


class RiskEvent(Base):
    """Risk management events"""
    __tablename__ = 'risk_events'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Event details
    event_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)  # 'low', 'medium', 'high', 'critical'
    description = Column(Text, nullable=False)

    # Context
    symbol = Column(String(20))
    strategy_name = Column(String(50))
    position_id = Column(Integer, ForeignKey('positions.id'))

    # Risk metrics at time of event
    portfolio_value = Column(Float)
    total_exposure = Column(Float)
    drawdown_percent = Column(Float)
    risk_level = Column(Float)

    # Actions taken
    action_taken = Column(Text)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)

    # Timestamps
    occurred_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Additional data
    extra_data = Column(JSON)

    # Relationships
    position = relationship("Position")

    # Indexes
    __table_args__ = (
        Index('idx_risk_events_type_severity', 'event_type', 'severity'),
        Index('idx_risk_events_time', 'occurred_at'),
        Index('idx_risk_events_resolved', 'resolved'),
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')",
                       name='check_valid_severity')
    )

    def __repr__(self):
        return f"<RiskEvent(id={self.id}, type={self.event_type}, severity={self.severity})>"


class Signal(Base):
    """Trading signal records"""
    __tablename__ = 'signals'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Signal identification
    strategy_name = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)

    # Signal details
    signal_type = Column(String(20), nullable=False)  # 'buy', 'sell', 'hold'
    strength = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    price = Column(Float, nullable=False)

    # Context
    reason = Column(Text)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    position_size = Column(Float)

    # Execution tracking
    executed = Column(Boolean, default=False)
    execution_price = Column(Float)
    execution_delay = Column(Float)  # seconds between signal and execution

    # Performance tracking
    outcome = Column(String(20))  # 'win', 'loss', 'pending'
    pnl = Column(Float)

    # Timestamps
    generated_at = Column(DateTime, nullable=False)
    executed_at = Column(DateTime)
    closed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())

    # Additional data
    indicators = Column(JSON)  # Store indicator values at signal time
    market_conditions = Column(JSON)
    extra_data = Column(JSON)

    # Indexes
    __table_args__ = (
        Index('idx_signals_strategy_symbol', 'strategy_name', 'symbol'),
        Index('idx_signals_time', 'generated_at'),
        Index('idx_signals_executed', 'executed'),
        Index('idx_signals_outcome', 'outcome'),
        CheckConstraint("signal_type IN ('buy', 'sell', 'hold')", name='check_valid_signal_type'),
        CheckConstraint('strength >= 0 AND strength <= 1', name='check_strength_range'),
        CheckConstraint('confidence >= 0 AND confidence <= 1', name='check_confidence_range')
    )

    def __repr__(self):
        return f"<Signal(id={self.id}, strategy={self.strategy_name}, type={self.signal_type}, strength={self.strength:.2f})>"


class BalanceSnapshot(Base):
    """Account balance snapshots"""
    __tablename__ = 'balance_snapshots'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Balance details
    total_balance = Column(Float, nullable=False)
    available_balance = Column(Float, nullable=False)
    used_balance = Column(Float, nullable=False)

    # Breakdown by asset
    asset_balances = Column(JSON)  # JSON object with asset-specific balances

    # P&L tracking
    daily_pnl = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)

    # Risk metrics
    margin_used = Column(Float, default=0.0)
    margin_available = Column(Float, default=0.0)
    margin_ratio = Column(Float, default=0.0)

    # Timestamp
    snapshot_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Additional data
    extra_data = Column(JSON)

    # Indexes
    __table_args__ = (
        Index('idx_balance_snapshots_time', 'snapshot_at'),
        CheckConstraint('total_balance >= 0', name='check_non_negative_balance'),
        CheckConstraint('available_balance >= 0', name='check_non_negative_available')
    )

    def __repr__(self):
        return f"<BalanceSnapshot(id={self.id}, total={self.total_balance}, time={self.snapshot_at})>"


class SystemEvent(Base):
    """System events and status changes"""
    __tablename__ = 'system_events'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Event details
    event_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)

    # Component information
    component = Column(String(50))
    module = Column(String(50))

    # Status
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)

    # Timestamps
    occurred_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Additional data
    details = Column(JSON)
    stack_trace = Column(Text)

    # Indexes
    __table_args__ = (
        Index('idx_system_events_type', 'event_type'),
        Index('idx_system_events_severity', 'severity'),
        Index('idx_system_events_time', 'occurred_at'),
        Index('idx_system_events_component', 'component'),
        CheckConstraint("severity IN ('info', 'warning', 'error', 'critical')",
                       name='check_valid_event_severity')
    )

    def __repr__(self):
        return f"<SystemEvent(id={self.id}, type={self.event_type}, severity={self.severity})>"


# Additional utility models for analytics
class DailyStats(Base):
    """Daily trading statistics"""
    __tablename__ = 'daily_stats'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Date
    date = Column(DateTime, nullable=False, unique=True)

    # Trading metrics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    daily_pnl = Column(Float, default=0.0)

    # Volume metrics
    total_volume = Column(Float, default=0.0)
    avg_trade_size = Column(Float, default=0.0)

    # Portfolio metrics
    starting_balance = Column(Float)
    ending_balance = Column(Float)
    max_drawdown = Column(Float, default=0.0)

    # Strategy breakdown
    strategy_stats = Column(JSON)

    # Market conditions
    market_conditions = Column(JSON)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_daily_stats_date', 'date'),
    )

    def __repr__(self):
        return f"<DailyStats(date={self.date.date()}, trades={self.total_trades}, pnl={self.daily_pnl:.2f})>"