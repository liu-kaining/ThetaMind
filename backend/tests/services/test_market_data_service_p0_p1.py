#!/usr/bin/env python3
"""Test script for P0 & P1 features of MarketDataService.

This script tests:
- P0: Risk metrics, Performance metrics, Efficiency ratios
- P1: Complete technical indicators, Financial statements, FinanceDatabase extensions
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.market_data_service import MarketDataService


def test_p0_features(service: MarketDataService, ticker: str = "AAPL"):
    """Test P0 priority features."""
    print("\n" + "=" * 80)
    print("  P0 Features Test")
    print("=" * 80)
    
    profile = service.get_financial_profile(ticker)
    
    # Test Efficiency Ratios
    print("\n[P0-1] Efficiency Ratios:")
    if "ratios" in profile and "efficiency" in profile["ratios"]:
        efficiency = profile["ratios"]["efficiency"]
        if efficiency:
            print(f"   ✅ Efficiency ratios retrieved: {len(efficiency)} data points")
            # Show first few keys
            sample_keys = list(efficiency.keys())[:3] if efficiency else []
            print(f"   Sample dates: {sample_keys}")
        else:
            print("   ⚠️  Efficiency ratios empty")
    else:
        print("   ❌ Efficiency ratios not found")
    
    # Test Risk Metrics
    print("\n[P0-2] Risk Metrics:")
    if "risk_metrics" in profile:
        risk = profile["risk_metrics"]
        if risk and "error" not in risk:
            print(f"   ✅ Risk metrics retrieved")
            print(f"   Available metrics: {list(risk.keys())}")
            if "all" in risk:
                print(f"   ✅ collect_all_metrics() successful")
            if "var" in risk:
                print(f"   ✅ VaR retrieved")
            if "max_drawdown" in risk:
                print(f"   ✅ Maximum Drawdown retrieved")
        else:
            print(f"   ⚠️  Risk metrics: {risk.get('error', 'empty')}")
    else:
        print("   ❌ Risk metrics not found")
    
    # Test Performance Metrics
    print("\n[P0-3] Performance Metrics:")
    if "performance_metrics" in profile:
        perf = profile["performance_metrics"]
        if perf and "error" not in perf:
            print(f"   ✅ Performance metrics retrieved")
            print(f"   Available metrics: {list(perf.keys())}")
            if "sharpe_ratio" in perf:
                print(f"   ✅ Sharpe Ratio retrieved")
            if "sortino_ratio" in perf:
                print(f"   ✅ Sortino Ratio retrieved")
            if "capm" in perf:
                print(f"   ✅ CAPM retrieved")
        else:
            print(f"   ⚠️  Performance metrics: {perf.get('error', 'empty')}")
    else:
        print("   ❌ Performance metrics not found")


def test_p1_features(service: MarketDataService, ticker: str = "AAPL"):
    """Test P1 priority features."""
    print("\n" + "=" * 80)
    print("  P1 Features Test")
    print("=" * 80)
    
    profile = service.get_financial_profile(ticker)
    
    # Test Complete Technical Indicators
    print("\n[P1-1] Complete Technical Indicators:")
    if "technical_indicators" in profile:
        tech = profile["technical_indicators"]
        if tech and "error" not in tech:
            print(f"   ✅ Technical indicators retrieved")
            print(f"   Available categories: {list(tech.keys())}")
            
            # Check for new indicators
            new_indicators = ["trend", "sma", "ema", "adx", "volatility", "atr", "volume", "obv"]
            found_new = [ind for ind in new_indicators if ind in tech]
            print(f"   ✅ New indicators found: {found_new}")
            
            if "trend" in tech:
                print(f"   ✅ Trend indicators (collect_trend_indicators) retrieved")
            if "volatility" in tech:
                print(f"   ✅ Volatility indicators (collect_volatility_indicators) retrieved")
            if "volume" in tech:
                print(f"   ✅ Volume indicators (collect_volume_indicators) retrieved")
        else:
            print(f"   ⚠️  Technical indicators: {tech.get('error', 'empty')}")
    else:
        print("   ❌ Technical indicators not found")
    
    # Test Financial Statements
    print("\n[P1-2] Financial Statements:")
    if "financial_statements" in profile:
        statements = profile["financial_statements"]
        if statements and "error" not in statements:
            print(f"   ✅ Financial statements retrieved")
            print(f"   Available statements: {list(statements.keys())}")
            
            if "income" in statements:
                income = statements["income"]
                if income:
                    print(f"   ✅ Income Statement retrieved: {len(income)} data points")
            if "balance" in statements:
                balance = statements["balance"]
                if balance:
                    print(f"   ✅ Balance Sheet retrieved: {len(balance)} data points")
            if "cash_flow" in statements:
                cashflow = statements["cash_flow"]
                if cashflow:
                    print(f"   ✅ Cash Flow Statement retrieved: {len(cashflow)} data points")
        else:
            print(f"   ⚠️  Financial statements: {statements.get('error', 'empty')}")
    else:
        print("   ❌ Financial statements not found")
    
    # Test FinanceDatabase Extensions
    print("\n[P1-3] FinanceDatabase Extensions:")
    
    # Test get_filter_options
    try:
        options = service.get_filter_options(country="United States")
        if options:
            print(f"   ✅ get_filter_options() successful")
            print(f"   Available filter fields: {list(options.keys())[:5]}...")
        else:
            print("   ⚠️  get_filter_options() returned empty")
    except Exception as e:
        print(f"   ❌ get_filter_options() failed: {e}")
    
    # Test search_tickers_by_name
    try:
        search_results = service.search_tickers_by_name("Apple", country="United States", limit=3)
        if search_results:
            print(f"   ✅ search_tickers_by_name() successful")
            print(f"   Found tickers: {search_results}")
        else:
            print("   ⚠️  search_tickers_by_name() returned empty")
    except Exception as e:
        print(f"   ❌ search_tickers_by_name() failed: {e}")
    
    # Test convert_to_toolkit
    try:
        test_tickers = ["AAPL", "MSFT"]
        toolkit = service.convert_to_toolkit(test_tickers)
        if toolkit:
            print(f"   ✅ convert_to_toolkit() successful")
            print(f"   Toolkit created for {len(test_tickers)} tickers")
        else:
            print("   ⚠️  convert_to_toolkit() returned None")
    except Exception as e:
        print(f"   ❌ convert_to_toolkit() failed: {e}")


def main():
    print("=" * 80)
    print("  MarketDataService P0 & P1 Features Test")
    print("=" * 80)
    
    # Initialize service
    print("\n[0] Initializing service...")
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
    
    # Test P0 features
    print("\n" + "=" * 80)
    print("  Testing P0 Features (Highest Priority)")
    print("=" * 80)
    test_p0_features(service, "AAPL")
    
    # Test P1 features
    print("\n" + "=" * 80)
    print("  Testing P1 Features (High Priority)")
    print("=" * 80)
    test_p1_features(service, "AAPL")
    
    # Summary
    print("\n" + "=" * 80)
    print("  Test Summary")
    print("=" * 80)
    print("✅ P0 & P1 features test completed!")
    print("\nNote: Some features may show warnings if:")
    print("  - FMP API is unavailable (will fallback to Yahoo Finance)")
    print("  - Certain methods are not available in the FinanceToolkit version")
    print("  - Network timeouts occur (this is normal for external APIs)")
    print("=" * 80)


if __name__ == "__main__":
    main()
