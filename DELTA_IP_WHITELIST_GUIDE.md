# 🛡️ Delta Exchange IP Whitelist Setup Guide

## 🔍 Step 1: Get Your Railway Server IP Address

I've added a special endpoint to your bot to show its public IP address. Visit:

```
https://bot-production-2cea.up.railway.app/api/ip-info
```

This will show you:
- **Public IP**: The IP address you need to whitelist
- **Instructions**: Step-by-step guide
- **Headers**: Additional connection information

## 📋 Step 2: Whitelist IP in Delta Exchange

### Method A: Add Specific IP (Recommended)

1. **Log into Delta Exchange**
   - Go to [Delta Exchange](https://app.india.delta.exchange)
   - Login with your account

2. **Navigate to API Management**
   - Click on your profile/account menu
   - Select **"API Management"** or **"API Keys"**

3. **Find Your API Key**
   - Look for the API key: `Jx3GNFer1ryFMA3c9t1m1DIt0w6ZqV`
   - Click **"Edit"** or **"Manage"** next to it

4. **Add IP Whitelist**
   - Look for **"IP Whitelist"** or **"Allowed IPs"** section
   - Add the IP address from the `/api/ip-info` endpoint
   - Example: `34.123.45.67` (use the actual IP from your bot)

5. **Save Changes**
   - Click **"Save"** or **"Update"**
   - The changes should take effect immediately

### Method B: Allow All IPs (Less Secure)

If you want to allow all IPs (not recommended for production):

1. In the IP Whitelist section, add: `0.0.0.0/0`
2. This allows connections from any IP address
3. **Warning**: This is less secure but easier for testing

## 🔧 Step 3: Test the Connection

After whitelisting, test your bot's connection:

### Test Endpoints:
```bash
# Check if API connection works
https://bot-production-2cea.up.railway.app/api/balance

# Check bot health
https://bot-production-2cea.up.railway.app/health

# Check bot status
https://bot-production-2cea.up.railway.app/status
```

### Expected Results:

**✅ If Whitelist Works:**
```json
{
  "total_balance": 1000.0,
  "available_balance": 950.0,
  "currency": "USDT"
}
```

**❌ If Still Blocked:**
```json
{
  "error": "IP not whitelisted",
  "code": "FORBIDDEN"
}
```

## 🚨 Common Issues & Solutions

### Issue 1: IP Address Changes
**Problem**: Railway may change your server's IP address
**Solution**:
- Use the `/api/ip-info` endpoint to check current IP
- Update whitelist if IP changes
- Consider using `0.0.0.0/0` for development

### Issue 2: Multiple IP Addresses
**Problem**: Your bot shows multiple IPs
**Solution**:
- Add all IPs shown in the `ip-info` response
- Railway may use different IPs for outbound connections

### Issue 3: API Still Not Working
**Checklist**:
- [ ] Correct API key in Railway environment variables
- [ ] IP address properly whitelisted in Delta Exchange
- [ ] API key has trading permissions enabled
- [ ] No typos in API credentials

## 🎯 Quick Verification Commands

Use these to test your setup:

```bash
# Get your server IP
curl https://bot-production-2cea.up.railway.app/api/ip-info

# Test API connection
curl https://bot-production-2cea.up.railway.app/api/balance

# Check health
curl https://bot-production-2cea.up.railway.app/health
```

## 📊 Delta Exchange API Permissions

Make sure your API key has these permissions:
- ✅ **Read Account Info** (for balance checks)
- ✅ **Read Positions** (for position monitoring)
- ✅ **Place Orders** (for trading)
- ✅ **Cancel Orders** (for risk management)
- ❌ **Withdraw Funds** (not needed, keep disabled for security)

## 🔄 Alternative: Dynamic IP Solution

If Railway's IP keeps changing, you can:

1. **Use a proxy service** with static IP
2. **Set up VPN** with fixed IP
3. **Use `0.0.0.0/0`** (accept from all IPs)

For most users, option 3 is simplest for trading bots.

## ✅ Final Verification

Once whitelisted:

1. **Visit your dashboard**: `https://bot-production-2cea.up.railway.app/`
2. **Check balance shows**: Real Delta Exchange balance
3. **Verify health**: Green status indicators
4. **Monitor logs**: No authentication errors

## 🎉 Success!

When properly whitelisted, your bot will:
- ✅ Connect to Delta Exchange successfully
- ✅ Show real account balance
- ✅ Execute trades automatically
- ✅ Monitor positions and risk
- ✅ Display live trading data

**Your automated trading bot is now ready for live operation! 🚀📈**

---

## 🆘 Need Help?

If you're still having issues:
1. Check the `/api/ip-info` endpoint for current IP
2. Verify API key permissions in Delta Exchange
3. Look at Railway logs for error messages
4. Ensure environment variables are set correctly

Your bot is deployed and ready - just needs the IP whitelist! 🎯