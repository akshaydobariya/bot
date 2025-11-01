#!/usr/bin/env python3
"""
Entry point script for Delta Exchange Trading Bot

This script provides a simple way to run the trading bot with
proper error handling and environment setup.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from src.main import main
    from src.utils.logger import logger
    from src.config import settings
    from src.web_interface import app as web_app
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)


def check_environment():
    """Check if environment is properly configured"""
    errors = []

    # Check API credentials
    if not settings.delta_api_key or settings.delta_api_key == "your_api_key_here":
        errors.append("DELTA_API_KEY is not configured")

    if not settings.delta_api_secret or settings.delta_api_secret == "your_api_secret_here":
        errors.append("DELTA_API_SECRET is not configured")

    # Check critical directories
    required_dirs = ["data", "logs"]
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            try:
                os.makedirs(dir_name)
                print(f"✅ Created {dir_name} directory")
            except Exception as e:
                errors.append(f"Cannot create {dir_name} directory: {e}")

    if errors:
        print("❌ Configuration errors found:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease check your .env file and ensure all required settings are configured.")
        return False

    return True


def print_startup_info():
    """Print startup information"""
    print("🚀 Delta Exchange Trading Bot")
    print("=" * 50)
    print(f"Environment: {settings.environment}")
    print(f"Log Level: {settings.log_level}")
    print(f"Base URL: {settings.delta_base_url}")
    print(f"Default Symbol: {settings.default_symbol}")
    print(f"Strategy: {settings.strategy}")
    print(f"Risk Management: {'Enabled' if settings.enable_risk_management else 'Disabled'}")
    print(f"Paper Trading: {'Enabled' if settings.enable_paper_trading else 'Disabled'}")
    print("=" * 50)


if __name__ == "__main__":
    import threading

    # Check if running in web mode (for cloud deployment)
    web_mode = os.environ.get('WEB_MODE', 'false').lower() == 'true'
    port = int(os.environ.get('PORT', 8000))

    if web_mode:
        print("🌐 Starting in web mode for cloud deployment...")
        print(f"📊 Dashboard will be available at: http://localhost:{port}")

        # Start web interface only
        web_app.run(host='0.0.0.0', port=port, debug=False)
    else:
        try:
            # Check environment configuration
            if not check_environment():
                sys.exit(1)

            # Print startup information
            print_startup_info()

            # Start web interface in background thread
            def run_web():
                web_app.run(host='0.0.0.0', port=port, debug=False)

            web_thread = threading.Thread(target=run_web, daemon=True)
            web_thread.start()

            print(f"🌐 Web dashboard started at: http://localhost:{port}")

            # Start the bot
            print("🎯 Starting trading bot...")
            asyncio.run(main())

        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Fatal error: {e}")
            logger.exception("Fatal error occurred")
            sys.exit(1)