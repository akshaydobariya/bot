"""
RSI Oversold/Overbought Trading Strategy for Delta Exchange

This strategy uses RSI (Relative Strength Index) to identify oversold and overbought conditions:
- Buy signal when RSI is oversold (< 30) and starts to recover
- Sell signal when RSI is overbought (> 70) and starts to decline
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional

from .base_strategy import BaseStrategy, TradingSignal, SignalType, OrderSide
from src.config import settings


class RSIStrategy(BaseStrategy):
    """
    RSI Oversold/Overbought Strategy

    Strategy Logic:
    1. Calculate RSI with specified period
    2. Identify oversold conditions (RSI < oversold_threshold)
    3. Identify overbought conditions (RSI > overbought_threshold)
    4. Generate BUY signals when RSI recovers from oversold
    5. Generate SELL signals when RSI declines from overbought
    6. Use additional confirmation with price momentum and volume
    """

    def __init__(self, client, product_id: int, symbol: str):
        super().__init__(client, product_id, symbol)

        # Strategy-specific parameters
        self.rsi_period = settings.rsi_period
        self.oversold_threshold = settings.rsi_oversold
        self.overbought_threshold = settings.rsi_overbought

        # Additional filters
        self.sma_period = 20  # For trend confirmation
        self.volume_period = 10  # For volume confirmation

        # Strategy state
        self.last_rsi = None
        self.last_position = 0
        self.consecutive_oversold = 0
        self.consecutive_overbought = 0

    def initialize(self) -> None:
        """Initialize strategy parameters"""
        print(f"Initializing RSI Strategy for {self.symbol}")
        print(f"RSI Period: {self.rsi_period}")
        print(f"Oversold Threshold: {self.oversold_threshold}")
        print(f"Overbought Threshold: {self.overbought_threshold}")
        print(f"SMA Period for trend: {self.sma_period}")

    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_sma(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average"""
        return data.rolling(window=period, min_periods=period).mean()

    def calculate_bollinger_bands(self, data: pd.Series, period: int = 20, std_dev: float = 2) -> tuple:
        """Calculate Bollinger Bands for additional confirmation"""
        sma = self.calculate_sma(data, period)
        std = data.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return upper_band, sma, lower_band

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators"""
        df = data.copy()

        # Calculate RSI
        df['rsi'] = self.calculate_rsi(df['close'], self.rsi_period)

        # Calculate SMA for trend confirmation
        df['sma'] = self.calculate_sma(df['close'], self.sma_period)

        # Calculate Bollinger Bands
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = self.calculate_bollinger_bands(df['close'])

        # Calculate price momentum
        df['price_change'] = df['close'].pct_change()
        df['price_momentum_3'] = df['close'].pct_change(periods=3)
        df['price_momentum_5'] = df['close'].pct_change(periods=5)

        # Calculate volume indicators if volume data is available
        if 'volume' in df.columns:
            df['volume_sma'] = self.calculate_sma(df['volume'], self.volume_period)
            df['volume_ratio'] = df['volume'] / df['volume_sma']
        else:
            df['volume_ratio'] = 1.0

        # RSI-based signals
        df['rsi_oversold'] = df['rsi'] < self.oversold_threshold
        df['rsi_overbought'] = df['rsi'] > self.overbought_threshold

        # RSI momentum (RSI change)
        df['rsi_change'] = df['rsi'].diff()
        df['rsi_momentum'] = df['rsi'].diff(periods=3)

        # Identify RSI recovery from oversold
        df['rsi_recovery_from_oversold'] = (
            (df['rsi'].shift(1) < self.oversold_threshold) &
            (df['rsi'] >= self.oversold_threshold) &
            (df['rsi_change'] > 0)
        )

        # Identify RSI decline from overbought
        df['rsi_decline_from_overbought'] = (
            (df['rsi'].shift(1) > self.overbought_threshold) &
            (df['rsi'] <= self.overbought_threshold) &
            (df['rsi_change'] < 0)
        )

        # Trend confirmation
        df['above_sma'] = df['close'] > df['sma']
        df['below_sma'] = df['close'] < df['sma']

        return df

    def calculate_signal_strength(self, row: pd.Series, signal_type: SignalType) -> float:
        """
        Calculate signal strength based on multiple RSI factors

        Args:
            row: Current data row with indicators
            signal_type: Type of signal being generated

        Returns:
            Signal strength between 0.0 and 1.0
        """
        strength = 0.0
        rsi = row.get('rsi', 50)

        if pd.isna(rsi):
            return 0.0

        if signal_type == SignalType.BUY:
            # Strength based on how oversold the RSI was
            if rsi <= self.oversold_threshold:
                oversold_strength = (self.oversold_threshold - rsi) / self.oversold_threshold
                strength += min(oversold_strength, 0.4)

            # RSI momentum (recovery strength)
            rsi_change = row.get('rsi_change', 0)
            if rsi_change > 0:
                strength += min(rsi_change / 10, 0.2)

            # Trend confirmation
            if row.get('above_sma', False):
                strength += 0.1

            # Price momentum confirmation
            price_momentum = row.get('price_momentum_3', 0)
            if price_momentum > 0:
                strength += min(price_momentum * 5, 0.15)

        elif signal_type == SignalType.SELL:
            # Strength based on how overbought the RSI was
            if rsi >= self.overbought_threshold:
                overbought_strength = (rsi - self.overbought_threshold) / (100 - self.overbought_threshold)
                strength += min(overbought_strength, 0.4)

            # RSI momentum (decline strength)
            rsi_change = row.get('rsi_change', 0)
            if rsi_change < 0:
                strength += min(abs(rsi_change) / 10, 0.2)

            # Trend confirmation
            if row.get('below_sma', False):
                strength += 0.1

            # Price momentum confirmation
            price_momentum = row.get('price_momentum_3', 0)
            if price_momentum < 0:
                strength += min(abs(price_momentum) * 5, 0.15)

        # Volume confirmation
        volume_ratio = row.get('volume_ratio', 1.0)
        if volume_ratio > 1.2:  # Above average volume
            strength += 0.1

        # Bollinger Bands confirmation
        price = row.get('close', 0)
        bb_lower = row.get('bb_lower', 0)
        bb_upper = row.get('bb_upper', 0)

        if signal_type == SignalType.BUY and price < bb_lower:
            strength += 0.1  # Price near lower Bollinger Band
        elif signal_type == SignalType.SELL and price > bb_upper:
            strength += 0.1  # Price near upper Bollinger Band

        return min(max(strength, 0.0), 1.0)

    def calculate_confidence(self, data: pd.DataFrame, current_idx: int) -> float:
        """Calculate signal confidence based on RSI pattern consistency"""
        confidence = 0.5

        if current_idx >= 10:
            recent_data = data.iloc[current_idx-10:current_idx+1]

            # Check RSI trend consistency
            rsi_values = recent_data['rsi'].dropna()
            if len(rsi_values) >= 5:
                # Check if RSI shows clear trend
                rsi_trend = np.polyfit(range(len(rsi_values)), rsi_values, 1)[0]

                if abs(rsi_trend) > 0.5:  # Strong RSI trend
                    confidence += 0.15

            # Check price-RSI divergence (higher confidence if they align)
            if len(recent_data) >= 5:
                price_change = recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]
                rsi_change = recent_data['rsi'].iloc[-1] - recent_data['rsi'].iloc[0]

                # If price and RSI move in same direction, increase confidence
                if (price_change > 0 and rsi_change > 0) or (price_change < 0 and rsi_change < 0):
                    confidence += 0.1

        # Market volatility consideration
        if current_idx >= 20:
            recent_returns = data['close'].iloc[current_idx-20:current_idx+1].pct_change()
            volatility = recent_returns.std()

            if volatility < 0.02:  # Low volatility
                confidence += 0.1
            elif volatility > 0.05:  # High volatility
                confidence -= 0.1

        return min(max(confidence, 0.0), 1.0)

    def generate_signal(self, data: pd.DataFrame) -> TradingSignal:
        """Generate trading signal based on RSI conditions"""
        if len(data) < max(self.rsi_period, self.sma_period) + 1:
            return TradingSignal(
                signal_type=SignalType.HOLD,
                strength=0.0,
                price=data['close'].iloc[-1] if not data.empty else 0.0,
                timestamp=datetime.now(),
                reason="Insufficient data for RSI calculation",
                confidence=0.0
            )

        current_row = data.iloc[-1]
        current_price = current_row['close']
        rsi = current_row.get('rsi', 50)

        signal_type = SignalType.HOLD
        reason = "No RSI signal"

        # Check for oversold recovery (BUY signal)
        if current_row.get('rsi_recovery_from_oversold', False):
            signal_type = SignalType.BUY
            reason = f"RSI recovery from oversold: {rsi:.1f}"

        # Alternative BUY condition: RSI very oversold and showing upward momentum
        elif rsi < self.oversold_threshold and current_row.get('rsi_change', 0) > 1:
            signal_type = SignalType.BUY
            reason = f"RSI oversold with upward momentum: {rsi:.1f}"

        # Check for overbought decline (SELL signal)
        elif current_row.get('rsi_decline_from_overbought', False):
            signal_type = SignalType.SELL
            reason = f"RSI decline from overbought: {rsi:.1f}"

        # Alternative SELL condition: RSI very overbought and showing downward momentum
        elif rsi > self.overbought_threshold and current_row.get('rsi_change', 0) < -1:
            signal_type = SignalType.SELL
            reason = f"RSI overbought with downward momentum: {rsi:.1f}"

        # Calculate signal strength and confidence
        strength = self.calculate_signal_strength(current_row, signal_type)
        confidence = self.calculate_confidence(data, len(data) - 1)

        # Apply additional filters
        if signal_type != SignalType.HOLD:
            # Trend filter
            if signal_type == SignalType.BUY and not current_row.get('above_sma', True):
                strength *= 0.8  # Reduce strength if buying against trend
                reason += " (against trend)"

            if signal_type == SignalType.SELL and not current_row.get('below_sma', True):
                strength *= 0.8  # Reduce strength if selling against trend
                reason += " (against trend)"

            # Volume filter
            volume_ratio = current_row.get('volume_ratio', 1.0)
            if volume_ratio < 0.8:  # Low volume
                strength *= 0.9
                reason += " (low volume)"

        # Calculate stop loss and take profit
        stop_loss = None
        take_profit = None

        if signal_type == SignalType.BUY:
            stop_loss = self.calculate_stop_loss_price(current_price, OrderSide.BUY)
            take_profit = self.calculate_take_profit_price(current_price, OrderSide.BUY)
        elif signal_type == SignalType.SELL:
            stop_loss = self.calculate_stop_loss_price(current_price, OrderSide.SELL)
            take_profit = self.calculate_take_profit_price(current_price, OrderSide.SELL)

        # Update internal state
        self.last_rsi = rsi

        return TradingSignal(
            signal_type=signal_type,
            strength=strength,
            price=current_price,
            timestamp=datetime.now(),
            reason=reason,
            confidence=confidence,
            stop_loss=stop_loss,
            take_profit=take_profit
        )

    def get_strategy_specific_info(self) -> dict:
        """Get strategy-specific information"""
        return {
            "strategy_type": "RSI Oversold/Overbought",
            "parameters": {
                "rsi_period": self.rsi_period,
                "oversold_threshold": self.oversold_threshold,
                "overbought_threshold": self.overbought_threshold,
                "sma_period": self.sma_period,
                "volume_period": self.volume_period
            },
            "current_state": {
                "last_rsi": self.last_rsi,
                "last_position": self.last_position,
                "consecutive_oversold": self.consecutive_oversold,
                "consecutive_overbought": self.consecutive_overbought
            }
        }