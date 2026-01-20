#!/usr/bin/env python3
"""Quick test script for MarketDataService with AAPL.

This can be run inside Docker container or virtual environment:
    docker-compose exec backend python test_market_service_aapl.py
    OR
    python test_market_service_aapl.py (in virtual environment)
"""

import sys
from pathlib import Path

# Ensure we can import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.services.market_data_service import MarketDataService


def main():
    print("=" * 80)
    print("  MarketDataService Test - AAPL")
    print("=" * 80)

    # Initialize service
    print("\n[1/4] Initializing service...")
    try:
        service = MarketDataService()
        print("✅ Service initialized")
        if service._fmp_api_key:
            print("   ✅ FMP API key configured")
        else:
            print("   ⚠️  FMP API key not set (using Yahoo Finance fallback)")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test financial profile
    print("\n[2/4] Fetching financial profile for AAPL...")
    try:
        profile = service.get_financial_profile("AAPL")
        if "error" in profile:
            print(f"❌ Error: {profile['error']}")
        else:
            print("✅ Financial profile retrieved")
            print(f"   Keys: {list(profile.keys())}")
            
            if "ratios" in profile and profile["ratios"]:
                ratio_keys = list(profile["ratios"].keys())
                print(f"   Ratios available: {ratio_keys}")
                
                # Show sample valuation ratio
                if "valuation" in profile["ratios"]:
                    valuation = profile["ratios"]["valuation"]
                    if valuation:
                        latest_date = list(valuation.keys())[-1] if valuation else None
                        if latest_date:
                            pe = valuation[latest_date].get("Price Earnings Ratio")
                            print(f"   Latest P/E Ratio: {pe}")
            
            if "profile" in profile and profile["profile"]:
                # Try different possible field names
                company = (
                    profile["profile"].get("Company Name") or
                    profile["profile"].get("name") or
                    profile["profile"].get("Name") or
                    "N/A"
                )
                market_cap = (
                    profile["profile"].get("Market Capitalization") or
                    profile["profile"].get("market_cap") or
                    profile["profile"].get("Market Cap") or
                    "N/A"
                )
                print(f"   Company: {company}")
                print(f"   Market Cap: {market_cap}")
                # Debug: print all profile keys if company is N/A
                if company == "N/A" and profile["profile"]:
                    print(f"   Profile keys: {list(profile['profile'].keys())[:5]}...")  # Show first 5 keys
    except Exception as e:
        print(f"❌ Error fetching profile: {e}")
        import traceback
        traceback.print_exc()

    # Test search
    print("\n[3/4] Testing ticker search...")
    try:
        tickers = service.search_tickers(
            sector="Information Technology",
            market_cap="Large Cap",
            country="United States",
            limit=5
        )
        print(f"✅ Found {len(tickers)} tickers")
        print(f"   Sample: {tickers[:5]}")
    except Exception as e:
        print(f"❌ Error searching: {e}")
        import traceback
        traceback.print_exc()

    # Test historical data
    print("\n[4/4] Fetching historical data for AAPL...")
    try:
        historical = service.get_historical_data("AAPL", period="monthly")
        if "error" in historical:
            print(f"⚠️  Warning: {historical['error']}")
        else:
            data = historical.get("data", {})
            if data:
                print(f"✅ Historical data retrieved: {len(data)} data points")
                dates = list(data.keys())
                if dates:
                    print(f"   Date range: {dates[0]} to {dates[-1]}")
            else:
                print("⚠️  No historical data available")
    except Exception as e:
        print(f"❌ Error fetching historical data: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("  Test completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
