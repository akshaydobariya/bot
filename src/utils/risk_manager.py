"""
Risk Management System for Delta Exchange Trading Bot

This module provides comprehensive risk management capabilities including:
- Position sizing
- Stop loss management
- Daily loss limits
- Drawdown protection
- Portfolio risk assessment
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import math

from src.api import DeltaExchangeClient, Position, Balance
from src.config import settings
from src.strategies.base_strategy import TradingSignal, SignalType


class RiskLevel(str, Enum):
    """Risk level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskMetrics:
    """Risk metrics data structure"""
    total_exposure: float
    position_risk: float
    account_risk: float
    daily_pnl: float
    max_drawdown: float
    var_95: float  # Value at Risk 95%
    sharpe_ratio: float
    risk_level: RiskLevel


@dataclass
class PositionRisk:
    """Individual position risk data"""
    product_id: int
    symbol: str
    size: float
    notional_value: float
    risk_percentage: float
    stop_loss_distance: float
    potential_loss: float


class RiskManager:
    """
    Comprehensive Risk Management System

    Features:
    - Real-time position monitoring
    - Automated stop loss management
    - Portfolio risk assessment
    - Daily loss limits
    - Drawdown protection
    - Risk-based position sizing
    """

    def __init__(self, client: DeltaExchangeClient):
        self.client = client

        # Risk management parameters from settings
        self.max_daily_loss = settings.max_daily_loss
        self.max_position_size = settings.max_position_size
        self.stop_loss_percentage = settings.stop_loss_percentage
        self.take_profit_percentage = settings.take_profit_percentage
        self.risk_percentage = settings.risk_percentage
        self.max_leverage = settings.max_leverage
        self.drawdown_limit = settings.drawdown_limit
        self.max_open_positions = settings.max_open_positions

        # Risk tracking
        self.daily_start_balance = 0.0
        self.peak_balance = 0.0
        self.current_drawdown = 0.0
        self.daily_pnl = 0.0
        self.trade_history = []

        # Risk state
        self.risk_breached = False
        self.emergency_stop = False
        self.last_risk_check = None

    def initialize_daily_tracking(self) -> None:
        """Initialize daily risk tracking"""
        try:
            balances = self.client.get_balances()
            if balances:
                total_balance = sum(float(b.available_balance) for b in balances if b.available_balance)
                self.daily_start_balance = total_balance
                if total_balance > self.peak_balance:
                    self.peak_balance = total_balance

                print(f"Risk Manager initialized - Daily start balance: ${self.daily_start_balance:.2f}")
        except Exception as e:
            print(f"Error initializing daily tracking: {e}")

    def calculate_position_size(self, signal: TradingSignal, account_balance: float,
                              current_price: float) -> float:
        """
        Calculate optimal position size based on risk management rules

        Args:
            signal: Trading signal
            account_balance: Current account balance
            current_price: Current market price

        Returns:
            Recommended position size
        """
        # Base position size using risk percentage
        risk_amount = account_balance * (self.risk_percentage / 100)

        # Calculate position size based on stop loss distance
        stop_loss_distance = self.stop_loss_percentage / 100
        max_loss_per_unit = current_price * stop_loss_distance

        if max_loss_per_unit > 0:
            base_size = risk_amount / max_loss_per_unit
        else:
            base_size = account_balance * 0.01  # 1% fallback

        # Adjust based on signal strength and confidence
        signal_multiplier = signal.strength * signal.confidence
        adjusted_size = base_size * signal_multiplier

        # Apply maximum position size limit
        max_notional = self.max_position_size
        max_size_by_notional = max_notional / current_price

        # Apply maximum leverage limit
        max_size_by_leverage = (account_balance * self.max_leverage) / current_price

        # Take the minimum of all constraints
        final_size = min(
            adjusted_size,
            max_size_by_notional,
            max_size_by_leverage,
            account_balance * 0.1 / current_price  # Max 10% of balance per position
        )

        return max(final_size, 0.001)  # Minimum position size

    def check_position_risk(self, position: Position, current_price: float) -> PositionRisk:
        """
        Assess risk for an individual position

        Args:
            position: Position object
            current_price: Current market price

        Returns:
            PositionRisk assessment
        """
        size = float(position.size)
        entry_price = float(position.entry_price)
        notional_value = abs(size * current_price)

        # Calculate potential loss with current stop loss percentage
        if size > 0:  # Long position
            stop_loss_price = entry_price * (1 - self.stop_loss_percentage / 100)
            potential_loss = (entry_price - stop_loss_price) * size
        else:  # Short position
            stop_loss_price = entry_price * (1 + self.stop_loss_percentage / 100)
            potential_loss = (stop_loss_price - entry_price) * abs(size)

        stop_loss_distance = abs(current_price - stop_loss_price) / current_price * 100

        # Calculate risk percentage relative to account
        try:
            balances = self.client.get_balances()
            total_balance = sum(float(b.available_balance) for b in balances if b.available_balance)
            risk_percentage = (potential_loss / total_balance) * 100 if total_balance > 0 else 0
        except:
            risk_percentage = 0

        return PositionRisk(
            product_id=position.product_id,
            symbol="",  # Would need to map product_id to symbol
            size=size,
            notional_value=notional_value,
            risk_percentage=risk_percentage,
            stop_loss_distance=stop_loss_distance,
            potential_loss=potential_loss
        )

    def assess_portfolio_risk(self) -> RiskMetrics:
        """
        Comprehensive portfolio risk assessment

        Returns:
            RiskMetrics with current portfolio risk data
        """
        try:
            # Get current positions and balances
            positions = self.client.get_positions()
            balances = self.client.get_balances()

            total_balance = sum(float(b.available_balance) for b in balances if b.available_balance)
            total_exposure = 0.0
            total_potential_loss = 0.0

            # Calculate portfolio exposure and risk
            for position in positions:
                current_price = float(position.mark_price)
                position_risk = self.check_position_risk(position, current_price)
                total_exposure += position_risk.notional_value
                total_potential_loss += position_risk.potential_loss

            # Calculate risk metrics
            exposure_ratio = total_exposure / total_balance if total_balance > 0 else 0
            position_risk_ratio = total_potential_loss / total_balance if total_balance > 0 else 0

            # Update drawdown calculation
            if total_balance > self.peak_balance:
                self.peak_balance = total_balance
                self.current_drawdown = 0.0
            else:
                self.current_drawdown = (self.peak_balance - total_balance) / self.peak_balance * 100

            # Calculate daily P&L
            self.daily_pnl = total_balance - self.daily_start_balance

            # Determine risk level
            risk_level = self._determine_risk_level(
                exposure_ratio, position_risk_ratio, self.current_drawdown, self.daily_pnl
            )

            return RiskMetrics(
                total_exposure=total_exposure,
                position_risk=position_risk_ratio,
                account_risk=exposure_ratio,
                daily_pnl=self.daily_pnl,
                max_drawdown=self.current_drawdown,
                var_95=total_potential_loss,  # Simplified VaR calculation
                sharpe_ratio=0.0,  # Would need historical returns to calculate
                risk_level=risk_level
            )

        except Exception as e:
            print(f"Error assessing portfolio risk: {e}")
            return RiskMetrics(
                total_exposure=0.0,
                position_risk=0.0,
                account_risk=0.0,
                daily_pnl=0.0,
                max_drawdown=0.0,
                var_95=0.0,
                sharpe_ratio=0.0,
                risk_level=RiskLevel.MEDIUM
            )

    def _determine_risk_level(self, exposure_ratio: float, position_risk: float,
                            drawdown: float, daily_pnl: float) -> RiskLevel:
        """Determine overall risk level based on multiple factors"""
        risk_score = 0

        # Exposure risk
        if exposure_ratio > 0.8:
            risk_score += 3
        elif exposure_ratio > 0.6:
            risk_score += 2
        elif exposure_ratio > 0.4:
            risk_score += 1

        # Position risk
        if position_risk > 0.1:  # 10% potential loss
            risk_score += 3
        elif position_risk > 0.05:
            risk_score += 2
        elif position_risk > 0.02:
            risk_score += 1

        # Drawdown risk
        if drawdown > self.drawdown_limit:
            risk_score += 4
        elif drawdown > self.drawdown_limit * 0.7:
            risk_score += 2
        elif drawdown > self.drawdown_limit * 0.5:
            risk_score += 1

        # Daily loss risk
        daily_loss_limit = self.max_daily_loss
        if daily_pnl < -daily_loss_limit:
            risk_score += 4
        elif daily_pnl < -daily_loss_limit * 0.7:
            risk_score += 2
        elif daily_pnl < -daily_loss_limit * 0.5:
            risk_score += 1

        # Determine risk level
        if risk_score >= 6:
            return RiskLevel.CRITICAL
        elif risk_score >= 4:
            return RiskLevel.HIGH
        elif risk_score >= 2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def should_allow_new_position(self, signal: TradingSignal, position_size: float,
                                 current_price: float) -> Tuple[bool, str]:
        """
        Check if a new position should be allowed based on risk rules

        Args:
            signal: Trading signal
            position_size: Proposed position size
            current_price: Current market price

        Returns:
            Tuple of (allowed, reason)
        """
        try:
            # Check emergency stop
            if self.emergency_stop:
                return False, "Emergency stop is active"

            # Get current risk assessment
            risk_metrics = self.assess_portfolio_risk()

            # Check daily loss limit
            if risk_metrics.daily_pnl <= -self.max_daily_loss:
                return False, f"Daily loss limit reached: ${risk_metrics.daily_pnl:.2f}"

            # Check drawdown limit
            if risk_metrics.max_drawdown >= self.drawdown_limit:
                return False, f"Maximum drawdown reached: {risk_metrics.max_drawdown:.2f}%"

            # Check maximum number of positions
            current_positions = len(self.client.get_positions())
            if current_positions >= self.max_open_positions:
                return False, f"Maximum number of positions reached: {current_positions}"

            # Check if risk level is too high
            if risk_metrics.risk_level == RiskLevel.CRITICAL:
                return False, "Portfolio risk level is critical"

            # Check position size limits
            notional_value = position_size * current_price
            if notional_value > self.max_position_size:
                return False, f"Position size too large: ${notional_value:.2f} > ${self.max_position_size:.2f}"

            # Check if adding this position would exceed portfolio limits
            new_exposure = risk_metrics.total_exposure + notional_value
            balances = self.client.get_balances()
            total_balance = sum(float(b.available_balance) for b in balances if b.available_balance)

            if new_exposure / total_balance > 0.9:  # Max 90% portfolio exposure
                return False, "Adding position would exceed portfolio exposure limit"

            # All checks passed
            return True, "Position allowed"

        except Exception as e:
            print(f"Error checking position allowance: {e}")
            return False, f"Error in risk check: {e}"

    def should_close_position(self, position: Position, current_price: float) -> Tuple[bool, str]:
        """
        Check if a position should be closed based on risk rules

        Args:
            position: Current position
            current_price: Current market price

        Returns:
            Tuple of (should_close, reason)
        """
        try:
            position_risk = self.check_position_risk(position, current_price)

            # Check if position risk is too high
            if position_risk.risk_percentage > 5.0:  # 5% of account at risk
                return True, f"Position risk too high: {position_risk.risk_percentage:.2f}%"

            # Check unrealized loss
            entry_price = float(position.entry_price)
            size = float(position.size)

            if size > 0:  # Long position
                unrealized_pnl = (current_price - entry_price) * size
                loss_percentage = (entry_price - current_price) / entry_price * 100
            else:  # Short position
                unrealized_pnl = (entry_price - current_price) * abs(size)
                loss_percentage = (current_price - entry_price) / entry_price * 100

            # Close if stop loss is hit
            if loss_percentage >= self.stop_loss_percentage:
                return True, f"Stop loss hit: {loss_percentage:.2f}%"

            # Close if take profit is hit
            profit_percentage = -loss_percentage  # Profit is negative loss
            if profit_percentage >= self.take_profit_percentage:
                return True, f"Take profit hit: {profit_percentage:.2f}%"

            return False, "Position within risk parameters"

        except Exception as e:
            print(f"Error checking position close: {e}")
            return False, f"Error in position check: {e}"

    def get_risk_report(self) -> Dict:
        """Get comprehensive risk report"""
        risk_metrics = self.assess_portfolio_risk()

        try:
            positions = self.client.get_positions()
            position_risks = []

            for position in positions:
                current_price = float(position.mark_price)
                pos_risk = self.check_position_risk(position, current_price)
                position_risks.append({
                    "product_id": pos_risk.product_id,
                    "size": pos_risk.size,
                    "notional_value": pos_risk.notional_value,
                    "risk_percentage": pos_risk.risk_percentage,
                    "potential_loss": pos_risk.potential_loss
                })
        except:
            position_risks = []

        return {
            "timestamp": datetime.now().isoformat(),
            "risk_metrics": {
                "total_exposure": risk_metrics.total_exposure,
                "position_risk": risk_metrics.position_risk,
                "account_risk": risk_metrics.account_risk,
                "daily_pnl": risk_metrics.daily_pnl,
                "max_drawdown": risk_metrics.max_drawdown,
                "risk_level": risk_metrics.risk_level.value
            },
            "position_risks": position_risks,
            "risk_limits": {
                "max_daily_loss": self.max_daily_loss,
                "max_position_size": self.max_position_size,
                "drawdown_limit": self.drawdown_limit,
                "max_open_positions": self.max_open_positions,
                "risk_percentage": self.risk_percentage
            },
            "risk_status": {
                "risk_breached": self.risk_breached,
                "emergency_stop": self.emergency_stop,
                "daily_start_balance": self.daily_start_balance,
                "peak_balance": self.peak_balance
            }
        }

    def emergency_close_all_positions(self) -> bool:
        """
        Emergency procedure to close all positions

        Returns:
            True if successful, False otherwise
        """
        try:
            print("EMERGENCY: Closing all positions")
            self.emergency_stop = True

            result = self.client.close_all_positions()
            print("All positions closed successfully")
            return True

        except Exception as e:
            print(f"Error closing all positions: {e}")
            return False

    def reset_daily_tracking(self) -> None:
        """Reset daily tracking (call at start of new trading day)"""
        self.initialize_daily_tracking()
        self.daily_pnl = 0.0
        self.risk_breached = False
        print("Daily risk tracking reset")