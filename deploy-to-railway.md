# 🚂 Deploy to Railway - Step by Step

**Railway.app is the best free platform for running your trading bot 24/7**

## 🎯 Complete Deployment Guide

### Step 1: Prepare Your Code

1. **Create GitHub Repository**
   - Go to [GitHub.com](https://github.com)
   - Click **"New repository"**
   - Name it: `delta-trading-bot`
   - Make it **Private** (recommended for trading bots)

2. **Upload Your Bot Files**
   - Download all files from this bot project
   - Upload them to your GitHub repository
   - **Important**: Don't upload the `.env` file (keep your API keys secure)

### Step 2: Deploy to Railway

1. **Create Railway Account**
   - Go to [Railway.app](https://railway.app)
   - Click **"Login"** → **"Login with GitHub"**
   - Authorize Railway to access your GitHub

2. **Create New Project**
   - Click **"New Project"**
   - Select **"Deploy from GitHub repo"**
   - Choose your `delta-trading-bot` repository
   - Click **"Deploy Now"**

3. **Railway Auto-Detection**
   - Railway will automatically detect it's a Python project
   - It will read `requirements.txt` and install dependencies
   - This takes 2-3 minutes

### Step 3: Configure Environment Variables

1. **Open Your Project**
   - Click on your deployed project in Railway dashboard
   - Go to **"Variables"** tab

2. **Add Required Variables**
   ```
   DELTA_API_KEY=Jx3GNFer1ryFMA3c9t1m1DIt0w6ZqV
   DELTA_API_SECRET=h2gGqrnc5nrvwQza2LgurFH1w0RSw0BtfSATKn5CKgySHqwDK5FmUpCKdbz
   WEB_MODE=true
   PORT=8000
   DATABASE_URL=sqlite:///data/trading_bot.db
   ENVIRONMENT=production
   ```

3. **Optional Variables** (for customization)
   ```
   DEFAULT_SYMBOL=BTCUSD
   RISK_PERCENTAGE=1.0
   STOP_LOSS_PERCENTAGE=2.0
   MAX_DAILY_LOSS=100.0
   STRATEGY=sma_crossover
   ENABLE_PAPER_TRADING=false
   ```

### Step 4: Deploy and Test

1. **Trigger Deployment**
   - After adding variables, Railway will automatically redeploy
   - Wait 2-3 minutes for deployment to complete

2. **Get Your URL**
   - In Railway dashboard, click **"Settings"** tab
   - Click **"Generate Domain"**
   - You'll get a URL like: `https://your-app.up.railway.app`

3. **Test Your Bot**
   - Visit your URL to see the dashboard
   - Check `/health` endpoint: `https://your-app.up.railway.app/health`
   - Should return: `{"status": "healthy"}`

### Step 5: Monitor Your Bot

**Dashboard Features:**
- 📊 Real-time trading metrics
- 💰 Portfolio value and P&L
- ⚠️ Risk level monitoring
- 📈 Recent trades and signals
- ❤️ Health status

**URLs to Bookmark:**
- **Main Dashboard**: `https://your-app.up.railway.app/`
- **Health Check**: `https://your-app.up.railway.app/health`
- **Bot Status**: `https://your-app.up.railway.app/status`
- **Recent Trades**: `https://your-app.up.railway.app/api/trades`

## 🔧 Railway Configuration Files

These files are already included in your bot:

### `railway.json`
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python run.py",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### `runtime.txt`
```
python-3.11.9
```

### `Procfile`
```
web: python run.py
```

## 💰 Railway Free Tier

**What You Get FREE:**
- ✅ $5 credit per month (enough for 24/7 running)
- ✅ 512MB RAM
- ✅ 1GB storage
- ✅ Custom domain
- ✅ Automatic deployments
- ✅ Environment variables
- ✅ 24/7 uptime

**Usage Calculator:**
- Small trading bot uses ~$0.01/hour
- $5 = ~500 hours = 20+ days of 24/7 running
- **Perfect for testing and small-scale trading**

## 🚨 Important Notes

### Security
- ✅ **Never commit API keys to GitHub**
- ✅ **Use Railway environment variables only**
- ✅ **Keep your repository private**

### Monitoring
- ✅ **Check dashboard daily**
- ✅ **Monitor your Delta Exchange account**
- ✅ **Watch for any error messages**

### Automatic Restarts
- ✅ **Railway automatically restarts failed deployments**
- ✅ **Your bot will resume trading after restart**
- ✅ **All data is saved in database**

## 🆘 Troubleshooting

### Deployment Failed
```bash
# Check these files exist in your repository:
✅ requirements.txt
✅ runtime.txt
✅ railway.json
✅ Procfile
✅ run.py
```

### Bot Not Starting
1. Check **Logs** tab in Railway dashboard
2. Verify environment variables are set
3. Ensure API credentials are correct

### Dashboard Not Loading
1. Check if `WEB_MODE=true` is set
2. Verify deployment completed successfully
3. Try visiting `/health` endpoint first

### Common Error Fixes
```bash
# If you see "Import Error":
- Check requirements.txt has all dependencies
- Verify Python version in runtime.txt

# If you see "API Authentication Failed":
- Double-check your DELTA_API_KEY and DELTA_API_SECRET
- Ensure no extra spaces in environment variables

# If you see "Database Error":
- DATABASE_URL should be: sqlite:///data/trading_bot.db
- Railway will create the data directory automatically
```

## 🎉 Success Checklist

Your bot is successfully deployed when you can:

- ✅ Visit your Railway URL and see the dashboard
- ✅ See "🟢 Running" status on the dashboard
- ✅ `/health` endpoint returns `{"status": "healthy"}`
- ✅ Dashboard shows your Delta Exchange connection
- ✅ Risk management is active
- ✅ Strategy is initialized

## 🚀 Next Steps

1. **Monitor Daily**: Check your dashboard and Delta Exchange account
2. **Adjust Settings**: Modify environment variables as needed
3. **Scale Up**: If profitable, consider upgrading Railway plan
4. **Add Alerts**: Set up monitoring notifications

## 📞 Support

- **Railway Issues**: Check Railway [documentation](https://docs.railway.app)
- **Bot Issues**: Review logs in Railway dashboard
- **Trading Issues**: Check your Delta Exchange account

**Your bot is now running 24/7 in the cloud! 🎊**

Railway URL: `https://your-app.up.railway.app`