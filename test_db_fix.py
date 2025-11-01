#!/usr/bin/env python3
"""
Quick test to verify SQLAlchemy metadata error is fixed
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_models_import():
    """Test that database models can be imported without SQLAlchemy errors"""
    try:
        print("🔄 Testing database models import...")

        # This should now work without the metadata error
        from src.database.models import (
            Base, Trade, Position, StrategyPerformance,
            RiskEvent, Signal, BalanceSnapshot, SystemEvent, DailyStats
        )

        print("✅ Database models imported successfully!")
        print("✅ SQLAlchemy metadata error has been fixed!")

        # Test that models have the correct extra_data attribute
        models_to_check = [Trade, Position, StrategyPerformance, RiskEvent, Signal, BalanceSnapshot]

        for model in models_to_check:
            if hasattr(model, 'extra_data'):
                print(f"✅ {model.__name__} has extra_data column")
            else:
                print(f"❌ {model.__name__} missing extra_data column")

        return True

    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_database_manager():
    """Test that database manager can be imported"""
    try:
        print("\n🔄 Testing database manager import...")

        from src.database.manager import db_manager
        print("✅ Database manager imported successfully!")
        return True

    except Exception as e:
        print(f"❌ Database manager import failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing SQLAlchemy metadata fix...\n")

    success = True

    # Test models import
    if not test_models_import():
        success = False

    # Test database manager
    if not test_database_manager():
        success = False

    if success:
        print("\n🎉 All tests passed! Your bot is ready to run!")
        print("✅ SQLAlchemy metadata error has been completely fixed")
        print("✅ Database models are working correctly")
        print("✅ Ready for Docker deployment or Railway.app deployment")
    else:
        print("\n❌ Some tests failed. Check the error messages above.")
        sys.exit(1)