"""
Configuration management for Delta Exchange Trading Bot
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import validator, Field
from enum import Enum


class Environment(str, Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(str, Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class TradingStrategy(str, Enum):
    """Available trading strategies"""
    SMA_CROSSOVER = "sma_crossover"
    RSI_OVERSOLD_OVERBOUGHT = "rsi_oversold_overbought"
    BOLLINGER_BANDS = "bollinger_bands"
    MACD_SIGNAL = "macd_signal"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"


class Settings(BaseSettings):
    """Application settings"""

    # Delta Exchange API Configuration
    delta_api_key: Optional[str] = Field(default=None, description="Delta Exchange API Key")
    delta_api_secret: Optional[str] = Field(default=None, description="Delta Exchange API Secret")
    delta_base_url: str = Field(
        default="https://api.india.delta.exchange",
        description="Delta Exchange Base URL"
    )
    delta_ws_url: str = Field(
        default="wss://stream.delta.exchange",
        description="Delta Exchange WebSocket URL"
    )

    # Environment Configuration
    environment: Environment = Field(default=Environment.PRODUCTION)
    log_level: LogLevel = Field(default=LogLevel.INFO)
    debug: bool = Field(default=False)

    # Database Configuration
    database_url: str = Field(
        default="sqlite:///data/trading_bot.db",
        description="Database connection URL"
    )

    # Trading Configuration
    default_symbol: str = Field(default="BTCUSD")
    default_quantity: float = Field(default=0.01, gt=0)
    max_position_size: float = Field(default=1.0, gt=0)
    stop_loss_percentage: float = Field(default=2.0, gt=0, le=50)
    take_profit_percentage: float = Field(default=3.0, gt=0, le=100)
    max_daily_loss: float = Field(default=100.0, gt=0)
    risk_percentage: float = Field(default=1.0, gt=0, le=10)
    max_leverage: int = Field(default=10, ge=1, le=100)

    # Trading Strategy Configuration
    strategy: TradingStrategy = Field(default=TradingStrategy.SMA_CROSSOVER)
    sma_short_period: int = Field(default=10, gt=0)
    sma_long_period: int = Field(default=30, gt=0)
    rsi_period: int = Field(default=14, gt=0)
    rsi_oversold: float = Field(default=30.0, ge=0, le=100)
    rsi_overbought: float = Field(default=70.0, ge=0, le=100)
    bollinger_period: int = Field(default=20, gt=0)
    bollinger_deviation: float = Field(default=2.0, gt=0)
    macd_fast: int = Field(default=12, gt=0)
    macd_slow: int = Field(default=26, gt=0)
    macd_signal: int = Field(default=9, gt=0)

    # Risk Management
    enable_risk_management: bool = Field(default=True)
    max_open_positions: int = Field(default=5, gt=0)
    min_account_balance: float = Field(default=50.0, gt=0)
    position_size_percentage: float = Field(default=2.0, gt=0, le=50)
    drawdown_limit: float = Field(default=10.0, gt=0, le=50)

    # WebSocket Configuration
    ws_reconnect_interval: int = Field(default=5, gt=0)
    ws_ping_interval: int = Field(default=30, gt=0)
    ws_max_reconnect_attempts: int = Field(default=10, gt=0)

    # Rate Limiting Configuration
    api_rate_limit: int = Field(default=100, gt=0)
    api_rate_window: int = Field(default=60, gt=0)

    # Notifications Configuration
    enable_telegram_notifications: bool = Field(default=False)
    telegram_bot_token: Optional[str] = Field(default=None)
    telegram_chat_id: Optional[str] = Field(default=None)

    enable_discord_notifications: bool = Field(default=False)
    discord_webhook_url: Optional[str] = Field(default=None)

    enable_email_notifications: bool = Field(default=False)
    smtp_host: Optional[str] = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_user: Optional[str] = Field(default=None)
    smtp_password: Optional[str] = Field(default=None)
    email_from: Optional[str] = Field(default=None)
    email_to: Optional[str] = Field(default=None)

    # Monitoring Configuration
    enable_prometheus_metrics: bool = Field(default=True)
    prometheus_port: int = Field(default=8000, ge=1024, le=65535)
    health_check_interval: int = Field(default=30, gt=0)

    # Backtesting Configuration
    backtest_start_date: str = Field(default="2023-01-01")
    backtest_end_date: str = Field(default="2023-12-31")
    backtest_initial_capital: float = Field(default=1000.0, gt=0)

    # Paper Trading
    enable_paper_trading: bool = Field(default=False)
    paper_trading_balance: float = Field(default=10000.0, gt=0)

    # Security
    jwt_secret_key: str = Field(..., min_length=32)
    encryption_key: str = Field(..., min_length=16)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator('sma_long_period')
    def validate_sma_periods(cls, v, values):
        """Ensure SMA long period is greater than short period"""
        if 'sma_short_period' in values and v <= values['sma_short_period']:
            raise ValueError('SMA long period must be greater than short period')
        return v

    @validator('rsi_overbought')
    def validate_rsi_levels(cls, v, values):
        """Ensure RSI overbought is greater than oversold"""
        if 'rsi_oversold' in values and v <= values['rsi_oversold']:
            raise ValueError('RSI overbought must be greater than oversold')
        return v

    @validator('macd_slow')
    def validate_macd_periods(cls, v, values):
        """Ensure MACD slow period is greater than fast period"""
        if 'macd_fast' in values and v <= values['macd_fast']:
            raise ValueError('MACD slow period must be greater than fast period')
        return v

    @validator('take_profit_percentage')
    def validate_profit_loss_ratio(cls, v, values):
        """Ensure take profit is greater than stop loss"""
        if 'stop_loss_percentage' in values and v <= values['stop_loss_percentage']:
            raise ValueError('Take profit percentage should typically be greater than stop loss percentage')
        return v

    def get_database_url(self) -> str:
        """Get database URL with proper path resolution"""
        if self.database_url.startswith("sqlite:///"):
            # Ensure data directory exists
            db_path = self.database_url.replace("sqlite:///", "")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return self.database_url

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == Environment.PRODUCTION

    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == Environment.DEVELOPMENT

    def is_testing(self) -> bool:
        """Check if running in testing environment"""
        return self.environment == Environment.TESTING

    def get_notification_settings(self) -> dict:
        """Get all notification settings"""
        return {
            "telegram": {
                "enabled": self.enable_telegram_notifications,
                "bot_token": self.telegram_bot_token,
                "chat_id": self.telegram_chat_id
            },
            "discord": {
                "enabled": self.enable_discord_notifications,
                "webhook_url": self.discord_webhook_url
            },
            "email": {
                "enabled": self.enable_email_notifications,
                "smtp_host": self.smtp_host,
                "smtp_port": self.smtp_port,
                "smtp_user": self.smtp_user,
                "smtp_password": self.smtp_password,
                "from": self.email_from,
                "to": self.email_to
            }
        }

    def get_strategy_config(self) -> dict:
        """Get strategy-specific configuration"""
        return {
            "strategy": self.strategy,
            "sma": {
                "short_period": self.sma_short_period,
                "long_period": self.sma_long_period
            },
            "rsi": {
                "period": self.rsi_period,
                "oversold": self.rsi_oversold,
                "overbought": self.rsi_overbought
            },
            "bollinger": {
                "period": self.bollinger_period,
                "deviation": self.bollinger_deviation
            },
            "macd": {
                "fast": self.macd_fast,
                "slow": self.macd_slow,
                "signal": self.macd_signal
            }
        }

    def get_risk_management_config(self) -> dict:
        """Get risk management configuration"""
        return {
            "enabled": self.enable_risk_management,
            "max_open_positions": self.max_open_positions,
            "min_account_balance": self.min_account_balance,
            "position_size_percentage": self.position_size_percentage,
            "drawdown_limit": self.drawdown_limit,
            "stop_loss_percentage": self.stop_loss_percentage,
            "take_profit_percentage": self.take_profit_percentage,
            "max_daily_loss": self.max_daily_loss,
            "risk_percentage": self.risk_percentage,
            "max_leverage": self.max_leverage
        }

    def validate_api_credentials(self) -> bool:
        """Validate that API credentials are present"""
        return bool(self.delta_api_key and self.delta_api_secret)

    def get_api_credentials_status(self) -> dict:
        """Get API credentials status"""
        return {
            "api_key_set": bool(self.delta_api_key),
            "api_secret_set": bool(self.delta_api_secret),
            "both_credentials_valid": self.validate_api_credentials()
        }


# Global settings instance with error handling
try:
    settings = Settings()
except Exception as e:
    print(f"⚠️ Settings validation error: {e}")
    print("💡 This might be due to missing environment variables")
    print("🔧 The bot will start in web-only mode")
    # Create settings with minimal configuration for web mode
    import os
    os.environ.setdefault('DELTA_API_KEY', 'not_set')
    os.environ.setdefault('DELTA_API_SECRET', 'not_set')
    settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance"""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment"""
    global settings
    settings = Settings()
    return settings