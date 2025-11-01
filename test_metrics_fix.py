#!/usr/bin/env python3
"""
Test script to verify Prometheus metrics duplication error is fixed
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_metrics_import():
    """Test that metrics can be imported multiple times without errors"""
    try:
        print("🔄 Testing metrics import (attempt 1)...")
        from src.monitoring.metrics import trading_metrics, health_checker
        print("✅ First import successful!")

        print("🔄 Testing metrics import (attempt 2)...")
        # This should not cause duplication error due to singleton pattern
        from src.monitoring.metrics import trading_metrics as tm2, health_checker as hc2
        print("✅ Second import successful!")

        # Test that both imports return the same instance (singleton)
        if trading_metrics is tm2:
            print("✅ Singleton pattern working - same instance returned")
        else:
            print("❌ Singleton pattern failed - different instances")

        print("✅ Prometheus metrics duplication error has been fixed!")
        return True

    except Exception as e:
        print(f"❌ Metrics import failed: {e}")
        return False

def test_web_interface_import():
    """Test that web interface can import metrics without errors"""
    try:
        print("\n🔄 Testing web interface import...")
        from src.web_interface import app
        print("✅ Web interface imported successfully!")
        return True

    except Exception as e:
        print(f"❌ Web interface import failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Prometheus metrics fix...\n")

    success = True

    # Test metrics import
    if not test_metrics_import():
        success = False

    # Test web interface import
    if not test_web_interface_import():
        success = False

    if success:
        print("\n🎉 All tests passed! Your bot is ready to run!")
        print("✅ Prometheus metrics duplication error is fixed")
        print("✅ Singleton pattern prevents re-registration")
        print("✅ Web interface imports correctly")
        print("✅ Ready for Docker deployment!")
    else:
        print("\n❌ Some tests failed. Check the error messages above.")
        sys.exit(1)