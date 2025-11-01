# Quick Start Guide - Delta Exchange Trading Bot

This guide will help you get the Delta Exchange Trading Bot up and running quickly.

## 🚀 Prerequisites

Before starting, ensure you have:

1. **Python 3.8+** installed on your system
2. **Delta Exchange India account** with API access enabled
3. **API credentials** from your Delta Exchange dashboard
4. **Sufficient balance** for trading (minimum recommended: $100)

## 📋 Step-by-Step Setup

### Step 1: Get Your API Credentials

1. Log in to your [Delta Exchange India account](https://app.india.delta.exchange/)
2. Go to **Settings** → **API Management**
3. Click **"Create a new API key"**
4. Configure the API key with these permissions:
   - ✅ **Read Data** (required)
   - ✅ **Trading** (required)
5. **Important**: Copy both API Key and API Secret immediately - you won't see the secret again!

### Step 2: Download and Install

```bash
# Clone or download the bot
git clone <repository-url>
cd Bot

# Run the installation script
bash scripts/install.sh
```

The installation script will:
- Check Python version compatibility
- Create a virtual environment
- Install all required dependencies
- Create necessary directories
- Copy environment configuration template

### Step 3: Configure Your Settings

Edit the `.env` file with your credentials:

```bash
# Open the environment file
nano .env  # or use your preferred editor
```

**Minimum required configuration:**

```env
# Delta Exchange API Configuration
DELTA_API_KEY=Jx3GNFer1ryFMA3c9t1m1DIt0w6ZqV
DELTA_API_SECRET=h2gGqrnc5nrvwQza2LgurFH1w0RSw0BtfSATKn5CKgySHqwDK5FmUpCKdbz

# Basic Trading Configuration
DEFAULT_SYMBOL=BTCUSD
DEFAULT_QUANTITY=0.01
RISK_PERCENTAGE=1.0
```

**Important Settings to Review:**
- `RISK_PERCENTAGE`: Start with 1.0% (risk 1% of your balance per trade)
- `STOP_LOSS_PERCENTAGE`: Default 2.0% (stop loss at 2% loss)
- `MAX_DAILY_LOSS`: Default $100 (maximum daily loss before bot stops)
- `ENABLE_PAPER_TRADING`: Set to `True` for testing without real money

### Step 4: Test Your Setup

Before live trading, test your configuration:

```bash
# Activate virtual environment
source venv/bin/activate

# Test API connection
python -c "
from src.api import DeltaExchangeClient
client = DeltaExchangeClient()
health = client.health_check()
print('API Status:', health.get('status'))
print('Connection: OK' if health.get('status') == 'healthy' else 'FAILED')
"
```

You should see:
```
API Status: healthy
Connection: OK
```

### Step 5: Start the Bot

```bash
# Run the trading bot
python run.py
```

You'll see output like:
```
🚀 Delta Exchange Trading Bot
==================================================
Environment: production
Log Level: INFO
Base URL: https://api.india.delta.exchange
Default Symbol: BTCUSD
Strategy: sma_crossover
Risk Management: Enabled
Paper Trading: Disabled
==================================================
🎯 Starting trading bot...
✅ API client initialized and healthy
✅ Risk manager initialized
✅ Strategies initialized
✅ Monitoring initialized
✅ Health checks configured
🚀 Trading Bot initialization complete
```

## 🛡️ Safety First - Important Notes

### For Beginners

1. **Start Small**: Begin with minimal position sizes
2. **Paper Trading**: Enable paper trading first to test strategies
3. **Monitor Closely**: Watch the bot for the first few hours
4. **Set Conservative Limits**: Use low risk percentages initially

### Risk Management Settings

```env
# Conservative settings for beginners
RISK_PERCENTAGE=0.5          # Risk only 0.5% per trade
MAX_DAILY_LOSS=50.0          # Stop after $50 daily loss
STOP_LOSS_PERCENTAGE=1.5     # Tight stop losses
MAX_OPEN_POSITIONS=2         # Limit concurrent positions
```

### Testing Configuration

```env
# Enable paper trading for testing
ENABLE_PAPER_TRADING=True
PAPER_TRADING_BALANCE=10000.0

# Or use very small real amounts
DEFAULT_QUANTITY=0.001       # Minimal position size
RISK_PERCENTAGE=0.1          # Very low risk
```

## 📊 Monitoring Your Bot

### Live Monitoring

1. **Console Output**: Watch real-time logs in your terminal
2. **Log Files**: Check detailed logs in the `logs/` directory
3. **Metrics Dashboard**: Access metrics at `http://localhost:8000/metrics`

### Key Metrics to Watch

- **Daily P&L**: Your profit/loss for the day
- **Win Rate**: Percentage of winning trades
- **Drawdown**: Maximum loss from peak
- **Risk Level**: Current portfolio risk (Low/Medium/High/Critical)

### Log Files

- `logs/trading_bot.log`: Main application log
- `logs/trades.jsonl`: All trade executions
- `logs/errors.log`: Error tracking
- `logs/risk_events.log`: Risk management events

## 🛑 How to Stop the Bot

### Normal Shutdown
Press `Ctrl+C` in the terminal - the bot will shut down gracefully and close all positions safely.

### Emergency Stop
If needed, you can manually close all positions in the Delta Exchange web interface.

## 🔧 Common Issues and Solutions

### Issue: "Authentication failed"
**Solution**: Double-check your API credentials in the `.env` file

### Issue: "Rate limit exceeded"
**Solution**: The bot has built-in rate limiting, but if you see this error, wait a few minutes

### Issue: "Insufficient balance"
**Solution**: Ensure you have enough balance for the configured position sizes

### Issue: Bot stops with "Risk limit reached"
**Solution**: This is intentional - check your risk settings and current positions

## 📚 Next Steps

Once your bot is running successfully:

1. **Read the Full Documentation**: See `README.md` for detailed configuration options
2. **Customize Strategies**: Explore different strategy parameters
3. **Set Up Monitoring**: Configure Prometheus and Grafana for advanced monitoring
4. **Optimize Performance**: Analyze trade history and adjust parameters

## 📞 Getting Help

- **Documentation**: Check `README.md` for comprehensive documentation
- **Logs**: Review log files in the `logs/` directory for error details
- **API Issues**: Verify your account status on Delta Exchange platform

## ⚠️ Final Reminders

1. **Never risk more than you can afford to lose**
2. **Start with paper trading or very small amounts**
3. **Monitor the bot closely, especially initially**
4. **Keep your API credentials secure**
5. **Regular backups of your configuration and logs**

---

**Ready to trade? Run `python run.py` and watch your bot start trading! 🚀**