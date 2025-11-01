"""
SMA Crossover Trading Strategy for Delta Exchange

This strategy uses Simple Moving Average crossovers to generate trading signals:
- Buy signal when short SMA crosses above long SMA
- Sell signal when short SMA crosses below long SMA
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional

from .base_strategy import BaseStrategy, TradingSignal, SignalType
from src.config import settings


class SMACrossoverStrategy(BaseStrategy):
    """
    Simple Moving Average Crossover Strategy

    Strategy Logic:
    1. Calculate short-term and long-term SMAs
    2. Generate BUY signal when short SMA crosses above long SMA
    3. Generate SELL signal when short SMA crosses below long SMA
    4. Use RSI as confirmation filter to avoid false signals
    """

    def __init__(self, client, product_id: int, symbol: str):
        super().__init__(client, product_id, symbol)

        # Strategy-specific parameters
        self.short_period = settings.sma_short_period
        self.long_period = settings.sma_long_period
        self.rsi_period = settings.rsi_period
        self.rsi_oversold = settings.rsi_oversold
        self.rsi_overbought = settings.rsi_overbought

        # Strategy state
        self.last_short_sma = None
        self.last_long_sma = None
        self.last_position = 0  # 1 for long, -1 for short, 0 for neutral

    def initialize(self) -> None:
        """Initialize strategy parameters"""
        print(f"Initializing SMA Crossover Strategy for {self.symbol}")
        print(f"Short SMA Period: {self.short_period}")
        print(f"Long SMA Period: {self.long_period}")
        print(f"RSI Period: {self.rsi_period}")
        print(f"RSI Oversold/Overbought: {self.rsi_oversold}/{self.rsi_overbought}")

    def calculate_sma(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average"""
        return data.rolling(window=period, min_periods=period).mean()

    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators"""
        df = data.copy()

        # Calculate SMAs
        df[f'sma_{self.short_period}'] = self.calculate_sma(df['close'], self.short_period)
        df[f'sma_{self.long_period}'] = self.calculate_sma(df['close'], self.long_period)

        # Calculate RSI for confirmation
        df['rsi'] = self.calculate_rsi(df['close'], self.rsi_period)

        # Calculate crossover signals
        df['sma_diff'] = df[f'sma_{self.short_period}'] - df[f'sma_{self.long_period}']
        df['sma_diff_prev'] = df['sma_diff'].shift(1)

        # Identify crossovers
        df['bullish_crossover'] = (
            (df['sma_diff'] > 0) & (df['sma_diff_prev'] <= 0)
        )
        df['bearish_crossover'] = (
            (df['sma_diff'] < 0) & (df['sma_diff_prev'] >= 0)
        )

        # Calculate signal strength based on price momentum and volume
        df['price_change'] = df['close'].pct_change()
        df['volume_ma'] = df['volume'].rolling(window=10).mean() if 'volume' in df.columns else 1

        return df

    def calculate_signal_strength(self, row: pd.Series) -> float:
        """
        Calculate signal strength based on multiple factors

        Args:
            row: Current data row with indicators

        Returns:
            Signal strength between 0.0 and 1.0
        """
        strength = 0.0

        # Base strength from SMA difference magnitude
        sma_short = row[f'sma_{self.short_period}']
        sma_long = row[f'sma_{self.long_period}']
        price = row['close']

        if pd.isna(sma_short) or pd.isna(sma_long):
            return 0.0

        # SMA difference as percentage of price
        sma_diff_pct = abs(sma_short - sma_long) / price * 100
        strength += min(sma_diff_pct / 2.0, 0.4)  # Max 0.4 from SMA difference

        # RSI confirmation
        rsi = row.get('rsi', 50)
        if not pd.isna(rsi):
            if rsi < self.rsi_oversold:  # Oversold - good for buy
                strength += 0.2
            elif rsi > self.rsi_overbought:  # Overbought - good for sell
                strength += 0.2
            elif 40 <= rsi <= 60:  # Neutral RSI
                strength += 0.1

        # Price momentum
        price_change = row.get('price_change', 0)
        if not pd.isna(price_change):
            momentum_strength = min(abs(price_change) * 10, 0.2)  # Max 0.2 from momentum
            strength += momentum_strength

        # Volume confirmation (if available)
        if 'volume' in row and 'volume_ma' in row:
            if row['volume'] > row['volume_ma'] * 1.2:  # Above average volume
                strength += 0.1

        # Ensure strength is between 0 and 1
        return min(max(strength, 0.0), 1.0)

    def calculate_confidence(self, data: pd.DataFrame, current_idx: int) -> float:
        """
        Calculate signal confidence based on historical performance and market conditions

        Args:
            data: DataFrame with indicators
            current_idx: Index of current row

        Returns:
            Confidence level between 0.0 and 1.0
        """
        confidence = 0.5  # Base confidence

        # Look at recent trend consistency
        if current_idx >= 5:
            recent_data = data.iloc[current_idx-5:current_idx+1]

            # Check if trend is consistent
            sma_short_col = f'sma_{self.short_period}'
            sma_long_col = f'sma_{self.long_period}'

            recent_diffs = recent_data[sma_short_col] - recent_data[sma_long_col]

            # If all recent differences have the same sign, increase confidence
            if len(recent_diffs.dropna()) > 0:
                if all(recent_diffs.dropna() > 0) or all(recent_diffs.dropna() < 0):
                    confidence += 0.2

        # Check volatility - lower volatility = higher confidence
        if current_idx >= 10:
            recent_returns = data['close'].iloc[current_idx-10:current_idx+1].pct_change()
            volatility = recent_returns.std()

            if volatility < 0.02:  # Low volatility
                confidence += 0.1
            elif volatility > 0.05:  # High volatility
                confidence -= 0.1

        # Ensure confidence is between 0 and 1
        return min(max(confidence, 0.0), 1.0)

    def generate_signal(self, data: pd.DataFrame) -> TradingSignal:
        """Generate trading signal based on SMA crossover"""
        if len(data) < max(self.short_period, self.long_period) + 1:
            return TradingSignal(
                signal_type=SignalType.HOLD,
                strength=0.0,
                price=data['close'].iloc[-1] if not data.empty else 0.0,
                timestamp=datetime.now(),
                reason="Insufficient data for SMA calculation",
                confidence=0.0
            )

        # Get the latest row
        current_row = data.iloc[-1]
        current_price = current_row['close']

        # Check for crossovers
        bullish_crossover = current_row.get('bullish_crossover', False)
        bearish_crossover = current_row.get('bearish_crossover', False)

        signal_type = SignalType.HOLD
        reason = "No crossover signal"

        if bullish_crossover:
            signal_type = SignalType.BUY
            reason = f"Bullish crossover: SMA{self.short_period} crossed above SMA{self.long_period}"
        elif bearish_crossover:
            signal_type = SignalType.SELL
            reason = f"Bearish crossover: SMA{self.short_period} crossed below SMA{self.long_period}"

        # Calculate signal strength and confidence
        strength = self.calculate_signal_strength(current_row)
        confidence = self.calculate_confidence(data, len(data) - 1)

        # Apply RSI filter for additional confirmation
        rsi = current_row.get('rsi', 50)
        if not pd.isna(rsi):
            if signal_type == SignalType.BUY and rsi > self.rsi_overbought:
                strength *= 0.7  # Reduce strength if buying in overbought condition
                reason += f" (RSI overbought: {rsi:.1f})"
            elif signal_type == SignalType.SELL and rsi < self.rsi_oversold:
                strength *= 0.7  # Reduce strength if selling in oversold condition
                reason += f" (RSI oversold: {rsi:.1f})"

        # Calculate stop loss and take profit levels
        stop_loss = None
        take_profit = None

        if signal_type == SignalType.BUY:
            stop_loss = self.calculate_stop_loss_price(current_price, OrderSide.BUY)
            take_profit = self.calculate_take_profit_price(current_price, OrderSide.BUY)
        elif signal_type == SignalType.SELL:
            stop_loss = self.calculate_stop_loss_price(current_price, OrderSide.SELL)
            take_profit = self.calculate_take_profit_price(current_price, OrderSide.SELL)

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
            "strategy_type": "SMA Crossover",
            "parameters": {
                "short_period": self.short_period,
                "long_period": self.long_period,
                "rsi_period": self.rsi_period,
                "rsi_oversold": self.rsi_oversold,
                "rsi_overbought": self.rsi_overbought
            },
            "current_state": {
                "last_short_sma": self.last_short_sma,
                "last_long_sma": self.last_long_sma,
                "last_position": self.last_position
            }
        }