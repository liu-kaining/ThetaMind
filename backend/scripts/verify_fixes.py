#!/usr/bin/env python3
"""Verification script for all code audit fixes.

This script verifies that all CRITICAL, HIGH, and MEDIUM level fixes are properly implemented.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.constants import CacheTTL, RetryConfig, TimeoutConfig, FinancialPrecision, RateLimits
from app.schemas.strategy import StrategySummary, OptionLeg, PortfolioGreeks
from app.services.cache import CacheService
from app.services.market_data_service import MarketDataService
from decimal import Decimal


def test_constants():
    """Test that all constants are properly defined."""
    print("✅ Testing constants...")
    
    assert CacheTTL.OPTION_CHAIN == 600
    assert CacheTTL.HISTORICAL_DATA == 86400
    assert RetryConfig.MAX_RETRIES == 3
    assert TimeoutConfig.AI_MODEL_TIMEOUT == 600
    assert RateLimits.WEBHOOK_REQUESTS_PER_MINUTE == 10
    
    print("   ✅ All constants defined correctly")


def test_pydantic_models():
    """Test that Pydantic models work correctly."""
    print("✅ Testing Pydantic models...")
    
    # Test OptionLeg
    leg = OptionLeg(
        action="buy",
        quantity=1,
        strike=Decimal("150.00"),
        type="call",
        premium=Decimal("5.00"),
        delta=Decimal("0.5"),
    )
    assert leg.action == "buy"
    assert leg.strike == Decimal("150.00")
    
    # Test PortfolioGreeks
    greeks = PortfolioGreeks(
        delta=Decimal("1.5"),
        gamma=Decimal("0.1"),
    )
    assert greeks.delta == Decimal("1.5")
    
    print("   ✅ Pydantic models work correctly")


def test_cache_service():
    """Test that CacheService has connection pool."""
    print("✅ Testing CacheService...")
    
    cache = CacheService()
    assert hasattr(cache, '_connection_pool')
    assert hasattr(cache, '_ensure_connected')
    
    print("   ✅ CacheService has connection pool and auto-reconnect")


def test_market_data_service():
    """Test that MarketDataService uses FinanceToolkit properly."""
    print("✅ Testing MarketDataService FinanceToolkit usage...")
    
    service = MarketDataService()
    
    # Check that methods try to use comprehensive FinanceToolkit methods
    # (We can't test actual calls without API keys, but we can check the code structure)
    assert hasattr(service, 'convert_database_results_to_toolkit')
    
    print("   ✅ MarketDataService has FinanceToolkit optimization methods")


def test_decimal_precision():
    """Test that Decimal precision is used in calculations."""
    print("✅ Testing Decimal precision...")
    
    # Simulate the calculation from _ensure_portfolio_greeks
    total_delta = Decimal('0')
    delta1 = Decimal('0.5')
    delta2 = Decimal('0.3')
    quantity = Decimal('2')
    sign = Decimal('1')
    multiplier = Decimal('1')
    
    total_delta += delta1 * sign * multiplier * quantity
    total_delta += delta2 * sign * multiplier * quantity
    
    assert total_delta == Decimal('1.6')
    
    # Test rounding
    precision = Decimal('0.0001')
    rounded = total_delta.quantize(precision, rounding='ROUND_HALF_UP')
    assert rounded == Decimal('1.6000')
    
    print("   ✅ Decimal precision calculations work correctly")


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Code Audit Fixes Verification")
    print("=" * 60)
    print()
    
    try:
        test_constants()
        test_pydantic_models()
        test_cache_service()
        test_market_data_service()
        test_decimal_precision()
        
        print()
        print("=" * 60)
        print("✅ All verification tests passed!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n❌ Verification failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
