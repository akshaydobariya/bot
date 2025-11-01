# Delta Exchange India Trading Bot

A production-ready algorithmic trading bot for Delta Exchange India, built with Python. This bot provides comprehensive trading automation with advanced risk management, monitoring, and multiple trading strategies.

## 🚀 Features

### Core Trading Features
- **Multiple Trading Strategies**: SMA Crossover, RSI Oversold/Overbought, and extensible framework for custom strategies
- **Real-time Market Data**: Live price feeds and technical indicators
- **Automated Order Execution**: Market orders, limit orders, stop-loss, and take-profit
- **Position Management**: Automatic position tracking and management

### Risk Management
- **Advanced Risk Controls**: Position sizing, daily loss limits, drawdown protection
- **Real-time Risk Monitoring**: Portfolio exposure tracking and risk level assessment
- **Emergency Stop Mechanisms**: Automatic position closure on critical risk events
- **Leverage Management**: Configurable leverage limits and margin monitoring

### Monitoring & Analytics
- **Comprehensive Logging**: Structured logging with multiple output formats
- **Performance Metrics**: Prometheus integration for real-time monitoring
- **Trade Analytics**: Win rate, profit factor, Sharpe ratio, and drawdown analysis
- **Health Monitoring**: System health checks and alerting

### Data Management
- **Persistent Storage**: SQLite/PostgreSQL database for trade history and analytics
- **Performance Tracking**: Strategy performance analysis and backtesting data
- **Risk Event Logging**: Complete audit trail of risk management decisions

## 📋 Prerequisites

- Python 3.8+
- Delta Exchange India API credentials
- Sufficient account balance for trading

## ⚡ Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd Bot
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your Delta Exchange API credentials:

```env
# Your API credentials from Delta Exchange India
DELTA_API_KEY=your_api_key_here
DELTA_API_SECRET=your_api_secret_here

# Trading configuration
DEFAULT_SYMBOL=BTCUSD
DEFAULT_QUANTITY=0.01
RISK_PERCENTAGE=1.0
STOP_LOSS_PERCENTAGE=2.0
TAKE_PROFIT_PERCENTAGE=3.0
```

### 3. Run the Bot

```bash
python src/main.py
```

## 🔧 Configuration

### Trading Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `DEFAULT_SYMBOL` | Trading pair symbol | BTCUSD |
| `DEFAULT_QUANTITY` | Base position size | 0.01 |
| `RISK_PERCENTAGE` | Risk per trade (% of balance) | 1.0 |
| `STOP_LOSS_PERCENTAGE` | Stop loss distance | 2.0 |
| `TAKE_PROFIT_PERCENTAGE` | Take profit distance | 3.0 |
| `MAX_DAILY_LOSS` | Maximum daily loss limit | 100.0 |

### Strategy Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `STRATEGY` | Active strategy name | sma_crossover |
| `SMA_SHORT_PERIOD` | Short SMA period | 10 |
| `SMA_LONG_PERIOD` | Long SMA period | 30 |
| `RSI_PERIOD` | RSI calculation period | 14 |
| `RSI_OVERSOLD` | RSI oversold threshold | 30 |
| `RSI_OVERBOUGHT` | RSI overbought threshold | 70 |

### Risk Management

| Parameter | Description | Default |
|-----------|-------------|---------|
| `MAX_POSITION_SIZE` | Maximum position size | 1.0 |
| `MAX_OPEN_POSITIONS` | Maximum concurrent positions | 5 |
| `DRAWDOWN_LIMIT` | Maximum drawdown (%) | 10.0 |
| `MAX_LEVERAGE` | Maximum leverage allowed | 10 |

## 📊 Available Strategies

### 1. SMA Crossover Strategy
- **Signal Generation**: Buy when short SMA crosses above long SMA, sell when short SMA crosses below long SMA
- **Confirmation**: RSI filter to avoid overbought/oversold conditions
- **Best For**: Trending markets with clear directional moves

### 2. RSI Oversold/Overbought Strategy
- **Signal Generation**: Buy on RSI oversold recovery, sell on RSI overbought decline
- **Confirmation**: Price momentum and volume confirmation
- **Best For**: Range-bound markets with clear support/resistance levels

### 3. Custom Strategies
The framework supports easy addition of custom strategies by extending the `BaseStrategy` class.

## 🛡️ Risk Management Features

### Position Sizing
- **Kelly Criterion**: Optimal position sizing based on win rate and profit/loss ratio
- **Fixed Percentage**: Risk a fixed percentage of account balance per trade
- **Volatility Adjustment**: Position size adjustment based on market volatility

### Risk Limits
- **Daily Loss Limit**: Automatic shutdown when daily loss limit is reached
- **Drawdown Protection**: Emergency stop when maximum drawdown is exceeded
- **Position Limits**: Maximum number of concurrent positions
- **Leverage Limits**: Maximum leverage per position and portfolio

### Real-time Monitoring
- **Risk Level Assessment**: Continuous portfolio risk evaluation (Low/Medium/High/Critical)
- **Exposure Tracking**: Real-time portfolio exposure monitoring
- **Margin Monitoring**: Margin usage and available margin tracking

## 📈 Monitoring & Analytics

### Prometheus Metrics
Access real-time metrics at `http://localhost:8000/metrics`:

- Trading performance metrics
- System resource usage
- API response times
- Error rates and types

### Logging
Structured logging with multiple outputs:

- **Console**: Real-time colored output
- **Files**: Rotating log files in `logs/` directory
- **JSON**: Structured logs for external processing

### Database Analytics
Comprehensive trade and performance data stored in SQLite/PostgreSQL:

- Trade history and P&L tracking
- Strategy performance analysis
- Risk event logging
- Daily/weekly/monthly statistics

## 🔍 API Integration

### Delta Exchange India API
- **Authentication**: Secure HMAC-SHA256 signature authentication
- **Rate Limiting**: Automatic rate limit compliance
- **Error Handling**: Comprehensive error handling and retry mechanisms
- **WebSocket**: Real-time market data (planned feature)

### Supported Operations
- Market data retrieval (tickers, orderbook, trades)
- Order management (place, cancel, modify orders)
- Position management (open, close, adjust margin)
- Account information (balances, positions, trade history)

## 🚨 Safety Features

### Emergency Stops
- **Keyboard Interrupt**: Graceful shutdown on Ctrl+C
- **Risk Breach**: Automatic shutdown on critical risk events
- **API Failures**: Automatic pause on persistent API failures

### Error Recovery
- **Automatic Retry**: Configurable retry mechanisms for transient failures
- **Circuit Breaker**: Temporary pause on repeated failures
- **Graceful Degradation**: Reduced functionality mode when components fail

## 📝 Logging and Debugging

### Log Levels
- **DEBUG**: Detailed execution information
- **INFO**: General operational information
- **WARNING**: Risk events and unusual conditions
- **ERROR**: Error conditions that don't stop operation
- **CRITICAL**: Fatal errors requiring immediate attention

### Log Files
- `logs/trading_bot.log`: Main application log
- `logs/errors.log`: Error-specific log
- `logs/trades.jsonl`: Structured trade execution log
- `logs/performance.jsonl`: Performance metrics log
- `logs/risk_events.log`: Risk management events

## 🔧 Development

### Project Structure
```
src/
├── api/                 # Delta Exchange API client
├── config/             # Configuration management
├── database/           # Database models and management
├── monitoring/         # Metrics and health checks
├── strategies/         # Trading strategies
├── utils/             # Utilities (logging, risk management)
└── main.py            # Main application entry point
```

### Adding Custom Strategies
1. Create a new strategy class extending `BaseStrategy`
2. Implement required methods: `initialize()`, `calculate_indicators()`, `generate_signal()`
3. Add strategy to the main application

### Testing
```bash
# Run unit tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Run specific test
pytest tests/test_strategies.py::TestSMAStrategy
```

## 🚀 Deployment

### Production Deployment
1. **Environment Setup**: Configure production environment variables
2. **Database**: Setup PostgreSQL for production use
3. **Monitoring**: Configure Prometheus and Grafana for monitoring
4. **Process Management**: Use supervisor or systemd for process management

### Docker Deployment (Coming Soon)
```bash
docker build -t delta-trading-bot .
docker run -d --env-file .env delta-trading-bot
```

## ⚠️ Disclaimers

1. **Trading Risk**: All trading involves risk. Past performance does not guarantee future results.
2. **No Warranty**: This software is provided as-is without any warranty.
3. **User Responsibility**: Users are responsible for their own trading decisions and risk management.
4. **Testing Required**: Always test strategies thoroughly before live trading.

## 📞 Support

- **Documentation**: Check this README and inline code documentation
- **Issues**: Report issues via GitHub Issues
- **API Documentation**: [Delta Exchange API Docs](https://docs.delta.exchange/)

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Delta Exchange for providing comprehensive API documentation
- The Python trading community for inspiration and best practices
- Contributors and testers who help improve the bot

---

**⚠️ Important**: This bot is for educational and research purposes. Always test with small amounts and never risk more than you can afford to lose. Trading cryptocurrencies involves substantial risk and may not be suitable for all investors.