"""
Base Strategy class for Delta Exchange Trading Bot
All trading strategies should inherit from this class
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
from datetime import datetime, timedelta

from src.api import DeltaExchangeClient, OrderRequest, OrderSide, OrderType, TimeInForce
from src.config import settings


class SignalType(str, Enum):
    """Trading signal types"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"


@dataclass
class TradingSignal:
    """Trading signal data structure"""
    signal_type: SignalType
    strength: float  # Signal strength (0.0 to 1.0)
    price: float
    timestamp: datetime
    reason: str
    confidence: float = 0.5  # Confidence level (0.0 to 1.0)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[float] = None


@dataclass
class StrategyState:
    """Strategy state tracking"""
    last_signal: Optional[TradingSignal] = None
    last_execution_time: Optional[datetime] = None
    consecutive_losses: int = 0
    consecutive_wins: int = 0
    total_trades: int = 0
    winning_trades: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    peak_value: float = 0.0


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies

    This class provides:
    - Common strategy interface
    - Risk management integration
    - Performance tracking
    - Signal generation framework
    - Position management utilities
    """

    def __init__(self, client: DeltaExchangeClient, product_id: int, symbol: str):
        self.client = client
        self.product_id = product_id
        self.symbol = symbol
        self.state = StrategyState()

        # Strategy parameters (can be overridden in subclasses)
        self.min_signal_strength = 0.6
        self.max_position_size = settings.max_position_size
        self.stop_loss_percentage = settings.stop_loss_percentage
        self.take_profit_percentage = settings.take_profit_percentage
        self.risk_percentage = settings.risk_percentage

        # Historical data
        self.price_data: Optional[pd.DataFrame] = None
        self.last_update_time: Optional[datetime] = None

        # Performance tracking
        self.performance_metrics = {
            "total_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0
        }

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize strategy-specific parameters and indicators
        Called once when the strategy is created
        """
        pass

    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators for the strategy

        Args:
            data: Price data DataFrame with OHLCV columns

        Returns:
            DataFrame with additional indicator columns
        """
        pass

    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> TradingSignal:
        """
        Generate trading signal based on current market data

        Args:
            data: Price data DataFrame with indicators

        Returns:
            TradingSignal object
        """
        pass

    def update_price_data(self, timeframe: str = "1m", limit: int = 100) -> pd.DataFrame:
        """Update price data from the exchange"""
        try:
            end_time = int(datetime.now().timestamp())
            start_time = end_time - (limit * 60)  # Assuming 1-minute intervals

            data = self.client.get_candles_as_dataframe(
                product_id=self.product_id,
                resolution=timeframe,
                start=start_time,
                end=end_time
            )

            if not data.empty:
                self.price_data = data
                self.last_update_time = datetime.now()

            return data

        except Exception as e:
            print(f"Error updating price data: {e}")
            return pd.DataFrame()

    def get_current_position(self) -> Optional[float]:
        """Get current position size for the product"""
        try:
            positions = self.client.get_positions()
            for position in positions:
                if position.product_id == self.product_id:
                    return float(position.size)
            return 0.0
        except Exception as e:
            print(f"Error getting current position: {e}")
            return None

    def calculate_position_size(self, signal: TradingSignal, account_balance: float) -> float:
        """
        Calculate optimal position size based on risk management rules

        Args:
            signal: Trading signal
            account_balance: Current account balance

        Returns:
            Position size to trade
        """
        # Base position size as percentage of account balance
        base_size = account_balance * (self.risk_percentage / 100)

        # Adjust based on signal strength and confidence
        strength_multiplier = signal.strength * signal.confidence
        adjusted_size = base_size * strength_multiplier

        # Apply maximum position size limit
        max_allowed = min(self.max_position_size, account_balance * 0.1)
        final_size = min(adjusted_size, max_allowed)

        # Use provided position size if specified
        if signal.position_size:
            final_size = min(signal.position_size, max_allowed)

        return round(final_size, 8)

    def calculate_stop_loss_price(self, entry_price: float, side: OrderSide) -> float:
        """Calculate stop loss price"""
        if side == OrderSide.BUY:
            return entry_price * (1 - self.stop_loss_percentage / 100)
        else:
            return entry_price * (1 + self.stop_loss_percentage / 100)

    def calculate_take_profit_price(self, entry_price: float, side: OrderSide) -> float:
        """Calculate take profit price"""
        if side == OrderSide.BUY:
            return entry_price * (1 + self.take_profit_percentage / 100)
        else:
            return entry_price * (1 - self.take_profit_percentage / 100)

    def should_execute_signal(self, signal: TradingSignal) -> bool:
        """
        Determine if a signal should be executed based on filters and risk management

        Args:
            signal: Trading signal to evaluate

        Returns:
            True if signal should be executed, False otherwise
        """
        # Check signal strength threshold
        if signal.strength < self.min_signal_strength:
            return False

        # Check confidence level
        if signal.confidence < 0.5:
            return False

        # Check time-based filters (avoid executing too frequently)
        if self.state.last_execution_time:
            time_since_last = datetime.now() - self.state.last_execution_time
            if time_since_last < timedelta(minutes=5):  # Minimum 5 minutes between trades
                return False

        # Check consecutive loss limit
        if self.state.consecutive_losses >= 3:  # Stop after 3 consecutive losses
            return False

        # Additional risk checks can be added here
        return True

    def execute_order(self, signal: TradingSignal, position_size: float) -> Optional[Dict[str, Any]]:
        """
        Execute order based on trading signal

        Args:
            signal: Trading signal
            position_size: Size of position to trade

        Returns:
            Order result or None if execution failed
        """
        try:
            # Determine order side
            if signal.signal_type in [SignalType.BUY]:
                side = OrderSide.BUY
            elif signal.signal_type in [SignalType.SELL, SignalType.CLOSE_LONG]:
                side = OrderSide.SELL
            else:
                return None  # No action for HOLD signals

            # Create order request
            order = OrderRequest(
                product_id=self.product_id,
                side=side,
                size=str(position_size),
                order_type=OrderType.MARKET,  # Use market orders for immediate execution
                time_in_force=TimeInForce.IOC
            )

            # Execute order
            result = self.client.place_order(order)

            # Update strategy state
            self.state.last_execution_time = datetime.now()
            self.state.total_trades += 1

            return result

        except Exception as e:
            print(f"Error executing order: {e}")
            return None

    def update_performance_metrics(self, trade_pnl: float) -> None:
        """Update strategy performance metrics"""
        self.state.total_pnl += trade_pnl

        if trade_pnl > 0:
            self.state.winning_trades += 1
            self.state.consecutive_wins += 1
            self.state.consecutive_losses = 0
        else:
            self.state.consecutive_losses += 1
            self.state.consecutive_wins = 0

        # Update peak value and drawdown
        if self.state.total_pnl > self.state.peak_value:
            self.state.peak_value = self.state.total_pnl

        current_drawdown = (self.state.peak_value - self.state.total_pnl) / max(self.state.peak_value, 1)
        if current_drawdown > self.state.max_drawdown:
            self.state.max_drawdown = current_drawdown

        # Calculate performance metrics
        if self.state.total_trades > 0:
            self.performance_metrics["win_rate"] = self.state.winning_trades / self.state.total_trades

        self.performance_metrics["total_return"] = self.state.total_pnl
        self.performance_metrics["max_drawdown"] = self.state.max_drawdown

    def run_iteration(self) -> Optional[TradingSignal]:
        """
        Run one iteration of the strategy

        Returns:
            Generated trading signal or None
        """
        try:
            # Update price data
            data = self.update_price_data()
            if data.empty:
                return None

            # Calculate indicators
            data_with_indicators = self.calculate_indicators(data)

            # Generate signal
            signal = self.generate_signal(data_with_indicators)

            # Store last signal
            self.state.last_signal = signal

            return signal

        except Exception as e:
            print(f"Error in strategy iteration: {e}")
            return None

    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information and current state"""
        return {
            "strategy_name": self.__class__.__name__,
            "symbol": self.symbol,
            "product_id": self.product_id,
            "state": {
                "total_trades": self.state.total_trades,
                "winning_trades": self.state.winning_trades,
                "consecutive_losses": self.state.consecutive_losses,
                "consecutive_wins": self.state.consecutive_wins,
                "total_pnl": self.state.total_pnl,
                "last_execution_time": self.state.last_execution_time.isoformat() if self.state.last_execution_time else None
            },
            "performance_metrics": self.performance_metrics,
            "last_signal": {
                "signal_type": self.state.last_signal.signal_type.value if self.state.last_signal else None,
                "strength": self.state.last_signal.strength if self.state.last_signal else None,
                "timestamp": self.state.last_signal.timestamp.isoformat() if self.state.last_signal else None
            } if self.state.last_signal else None,
            "last_update_time": self.last_update_time.isoformat() if self.last_update_time else None
        }

    def reset_state(self) -> None:
        """Reset strategy state (useful for backtesting or restart)"""
        self.state = StrategyState()
        self.performance_metrics = {
            "total_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0
        }