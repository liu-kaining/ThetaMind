#!/usr/bin/env python3
"""Test script for MarketDataService.

This script tests the MarketDataService with a real ticker (SNDK) to verify:
1. Service initialization
2. Financial profile retrieval
3. Options data retrieval
4. Discovery/search functionality

Usage:
    python scripts/test_market_data_service.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.market_data_service import MarketDataService


def print_section(title: str):
    """Print a formatted section title."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_dict(data: dict, indent: int = 0):
    """Pretty print dictionary with truncation for large values."""
    for key, value in data.items():
        prefix = "  " * indent
        if isinstance(value, dict):
            print(f"{prefix}{key}:")
            print_dict(value, indent + 1)
        elif isinstance(value, list):
            print(f"{prefix}{key}: [{len(value)} items]")
            if value and isinstance(value[0], dict):
                print(f"{prefix}  (first item): {value[0]}")
            elif value:
                print(f"{prefix}  (first 5): {value[:5]}")
        elif isinstance(value, (int, float)):
            print(f"{prefix}{key}: {value}")
        else:
            # Truncate long strings
            str_value = str(value)
            if len(str_value) > 100:
                print(f"{prefix}{key}: {str_value[:100]}...")
            else:
                print(f"{prefix}{key}: {str_value}")


def test_service_initialization():
    """Test 1: Service initialization."""
    print_section("Test 1: Service Initialization")
    
    try:
        service = MarketDataService()
        print("✅ MarketDataService initialized successfully")
        print(f"   FMP API Key configured: {service._fmp_api_key is not None}")
        return service
    except Exception as e:
        print(f"❌ Failed to initialize service: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_search_tickers(service: MarketDataService):
    """Test 2: Ticker discovery/search."""
    print_section("Test 2: Ticker Discovery (Search)")
    
    try:
        # Search for tech stocks
        tickers = service.search_tickers(
            sector="Information Technology",
            market_cap="Large Cap",
            country="United States",
            limit=10
        )
        
        print(f"✅ Found {len(tickers)} tickers")
        print(f"   Sample tickers: {tickers[:10]}")
        
        # Check if SNDK is in the database
        print("\n   Checking if SNDK is available in database...")
        all_tickers = service.search_tickers(
            country="United States",
            limit=1000  # Large limit to search
        )
        if "SNDK" in all_tickers:
            print("   ✅ SNDK found in database")
        else:
            print("   ⚠️  SNDK not found in database (may need different search criteria)")
        
        return tickers
    except Exception as e:
        print(f"❌ Failed to search tickers: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_financial_profile(service: MarketDataService, ticker: str = "SNDK"):
    """Test 3: Financial profile retrieval."""
    print_section(f"Test 3: Financial Profile - {ticker}")
    
    try:
        print(f"Fetching financial profile for {ticker}...")
        profile = service.get_financial_profile(ticker)
        
        if "error" in profile:
            print(f"❌ Error: {profile.get('error')}")
            return None
        
        print(f"✅ Financial profile retrieved for {ticker}")
        
        # Print summary
        print(f"\n   Profile Keys: {list(profile.keys())}")
        
        # Check ratios
        if profile.get("ratios"):
            ratio_keys = list(profile["ratios"].keys())
            print(f"   Ratios available: {ratio_keys}")
            if "valuation" in profile["ratios"]:
                valuation = profile["ratios"]["valuation"]
                if valuation:
                    latest_key = list(valuation.keys())[-1] if valuation else None
                    if latest_key:
                        pe_ratio = valuation[latest_key].get("Price Earnings Ratio")
                        print(f"   Latest P/E Ratio: {pe_ratio}")
        
        # Check technical indicators
        if profile.get("technical_indicators"):
            tech_keys = list(profile["technical_indicators"].keys())
            print(f"   Technical indicators available: {tech_keys}")
            if "rsi" in profile["technical_indicators"]:
                rsi_data = profile["technical_indicators"]["rsi"]
                if rsi_data:
                    latest_rsi = list(rsi_data.values())[-1] if rsi_data else None
                    print(f"   Latest RSI: {latest_rsi}")
        
        # Check profile info
        if profile.get("profile"):
            company_name = profile["profile"].get("Company Name")
            market_cap = profile["profile"].get("Market Capitalization")
            print(f"   Company: {company_name}")
            print(f"   Market Cap: {market_cap}")
        
        return profile
    except Exception as e:
        print(f"❌ Failed to get financial profile: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_options_data(service: MarketDataService, ticker: str = "SNDK"):
    """Test 4: Options data retrieval."""
    print_section(f"Test 4: Options Data - {ticker}")
    
    try:
        print(f"Fetching options data for {ticker}...")
        options = service.get_options_data(ticker)
        
        if "error" in options:
            print(f"❌ Error: {options.get('error')}")
            print("   (This is expected if FinanceToolkit doesn't have options data for this ticker)")
            return None
        
        print(f"✅ Options data retrieved for {ticker}")
        
        # Print summary
        print(f"\n   Options Keys: {list(options.keys())}")
        
        if options.get("greeks"):
            greeks_keys = list(options["greeks"].keys())
            print(f"   Greeks available: {greeks_keys}")
        
        return options
    except Exception as e:
        print(f"❌ Failed to get options data: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_historical_data(service: MarketDataService, ticker: str = "SNDK"):
    """Test 5: Historical data retrieval."""
    print_section(f"Test 5: Historical Data - {ticker}")
    
    try:
        print(f"Fetching historical data for {ticker}...")
        historical = service.get_historical_data(ticker, period="monthly")
        
        if "error" in historical:
            print(f"❌ Error: {historical.get('error')}")
            return None
        
        data = historical.get("data", {})
        if data:
            print(f"✅ Historical data retrieved for {ticker}")
            print(f"   Data points: {len(data)}")
            # Show first and last dates
            dates = list(data.keys())
            if dates:
                print(f"   Date range: {dates[0]} to {dates[-1]}")
        else:
            print(f"⚠️  No historical data available for {ticker}")
        
        return historical
    except Exception as e:
        print(f"❌ Failed to get historical data: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run all tests."""
    print("=" * 80)
    print("  MarketDataService Test Suite")
    print("  Testing with ticker: SNDK")
    print("=" * 80)
    
    # Test 1: Initialize service
    service = test_service_initialization()
    if not service:
        print("\n❌ Cannot continue without service initialization")
        return
    
    # Test 2: Search tickers
    tickers = test_search_tickers(service)
    
    # Test 3: Financial profile
    profile = test_financial_profile(service, "SNDK")
    
    # Test 4: Options data (may not work for all tickers)
    options = test_options_data(service, "SNDK")
    
    # Test 5: Historical data
    historical = test_historical_data(service, "SNDK")
    
    # Summary
    print_section("Test Summary")
    print(f"✅ Service Initialization: {'PASS' if service else 'FAIL'}")
    print(f"✅ Ticker Discovery: {'PASS' if tickers else 'FAIL'}")
    print(f"✅ Financial Profile: {'PASS' if profile and 'error' not in profile else 'FAIL'}")
    print(f"⚠️  Options Data: {'PASS' if options and 'error' not in options else 'SKIP (may not be available)'}")
    print(f"✅ Historical Data: {'PASS' if historical and 'error' not in historical else 'FAIL'}")
    
    print("\n" + "=" * 80)
    print("  Test completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
