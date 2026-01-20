#!/usr/bin/env python3
"""Test script for P2 & P3 features of MarketDataService.

This script tests:
- P2: Valuation models (DCF, DDM, DuPont), Analysis functions
- P3: Chart generation, ETF support
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.market_data_service import MarketDataService


def test_p2_features(service: MarketDataService, ticker: str = "AAPL"):
    """Test P2 priority features."""
    print("\n" + "=" * 80)
    print("  P2 Features Test")
    print("=" * 80)
    
    profile = service.get_financial_profile(ticker)
    
    # Test Valuation Models
    print("\n[P2-1] Valuation Models:")
    if "valuation" in profile:
        valuation = profile["valuation"]
        if valuation and "error" not in valuation:
            print(f"   ✅ Valuation models retrieved")
            print(f"   Available models: {list(valuation.keys())}")
            
            if "dcf" in valuation:
                print(f"   ✅ DCF (Intrinsic Valuation) retrieved")
            if "ddm" in valuation:
                print(f"   ✅ DDM (Dividend Discount Model) retrieved")
            if "wacc" in valuation:
                print(f"   ✅ WACC (Weighted Average Cost of Capital) retrieved")
            if "enterprise_value" in valuation:
                print(f"   ✅ Enterprise Value Breakdown retrieved")
        else:
            print(f"   ⚠️  Valuation models: {valuation.get('error', 'empty')}")
    else:
        print("   ❌ Valuation models not found")
    
    # Test DuPont Analysis
    print("\n[P2-2] DuPont Analysis:")
    if "dupont_analysis" in profile:
        dupont = profile["dupont_analysis"]
        if dupont and "error" not in dupont:
            print(f"   ✅ DuPont analysis retrieved")
            print(f"   Available analysis: {list(dupont.keys())}")
            
            if "standard" in dupont:
                print(f"   ✅ Standard DuPont Analysis retrieved")
            if "extended" in dupont:
                print(f"   ✅ Extended DuPont Analysis retrieved")
        else:
            print(f"   ⚠️  DuPont analysis: {dupont.get('error', 'empty')}")
    else:
        print("   ❌ DuPont analysis not found")
    
    # Test Analysis (Signals, Scores)
    print("\n[P2-3] Analysis (Signals & Scores):")
    if "analysis" in profile:
        analysis = profile["analysis"]
        if analysis and "error" not in analysis:
            print(f"   ✅ Analysis generated")
            print(f"   Available analysis: {list(analysis.keys())}")
            
            if "technical_signals" in analysis:
                signals = analysis["technical_signals"]
                print(f"   ✅ Technical signals: {list(signals.keys())}")
                if "rsi" in signals:
                    print(f"      RSI signal: {signals.get('rsi')} (value: {signals.get('rsi_value', 'N/A')})")
            
            if "risk_score" in analysis:
                risk = analysis["risk_score"]
                print(f"   ✅ Risk score: {risk.get('overall', 'N/A')} ({risk.get('category', 'N/A')})")
                print(f"      Factors: {risk.get('factors', [])}")
            
            if "health_score" in analysis:
                health = analysis["health_score"]
                print(f"   ✅ Health score: {health.get('overall', 'N/A')} ({health.get('category', 'N/A')})")
                print(f"      Factors: {health.get('factors', [])}")
            
            if "warnings" in analysis:
                warnings = analysis["warnings"]
                if warnings:
                    print(f"   ⚠️  Warnings: {len(warnings)}")
                    for warning in warnings[:3]:  # Show first 3
                        print(f"      - {warning}")
        else:
            print(f"   ⚠️  Analysis: {analysis.get('error', 'empty')}")
    else:
        print("   ❌ Analysis not found")


def test_p3_features(service: MarketDataService, ticker: str = "AAPL"):
    """Test P3 priority features."""
    print("\n" + "=" * 80)
    print("  P3 Features Test")
    print("=" * 80)
    
    # Test Chart Generation
    print("\n[P3-1] Chart Generation:")
    
    # Test ratios chart
    try:
        ratios_chart = service.generate_ratios_chart(ticker, ratio_type="profitability")
        if ratios_chart:
            print(f"   ✅ generate_ratios_chart() successful")
            print(f"      Chart size: {len(ratios_chart)} bytes (base64)")
        else:
            print("   ⚠️  generate_ratios_chart() returned None (may need matplotlib)")
    except Exception as e:
        print(f"   ⚠️  generate_ratios_chart() failed: {e}")
    
    # Test technical chart
    try:
        tech_chart = service.generate_technical_chart(ticker, indicator="rsi")
        if tech_chart:
            print(f"   ✅ generate_technical_chart() successful")
            print(f"      Chart size: {len(tech_chart)} bytes (base64)")
        else:
            print("   ⚠️  generate_technical_chart() returned None (may need matplotlib)")
    except Exception as e:
        print(f"   ⚠️  generate_technical_chart() failed: {e}")
    
    # Test ETF Support
    print("\n[P3-2] ETF Support:")
    try:
        # Try without category_group first (let the service check available options)
        etfs = service.search_etfs(
            country="United States",
            limit=5
        )
        if etfs:
            print(f"   ✅ search_etfs() successful")
            print(f"      Found {len(etfs)} ETFs")
            print(f"      Sample: {etfs[:5]}")
        else:
            print("   ⚠️  search_etfs() returned empty")
    except Exception as e:
        print(f"   ⚠️  search_etfs() failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    print("=" * 80)
    print("  MarketDataService P2 & P3 Features Test")
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
    
    # Test P2 features
    print("\n" + "=" * 80)
    print("  Testing P2 Features (Medium Priority)")
    print("=" * 80)
    test_p2_features(service, "AAPL")
    
    # Test P3 features
    print("\n" + "=" * 80)
    print("  Testing P3 Features (Low Priority)")
    print("=" * 80)
    test_p3_features(service, "AAPL")
    
    # Summary
    print("\n" + "=" * 80)
    print("  Test Summary")
    print("=" * 80)
    print("✅ P2 & P3 features test completed!")
    print("\nNote: Some features may show warnings if:")
    print("  - FMP API is unavailable (will fallback to Yahoo Finance)")
    print("  - Certain methods are not available in the FinanceToolkit version")
    print("  - Matplotlib is not installed (required for chart generation)")
    print("=" * 80)


if __name__ == "__main__":
    main()
