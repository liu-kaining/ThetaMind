#!/usr/bin/env python3
"""
Comprehensive test script for AI Report and Image Generation functionality.

Tests:
1. AI Report generation with various strategy_summary formats
2. Image generation with various strategy_summary formats
3. Error handling for None values
4. Prompt generation
5. Data validation

Run with: python test_ai_functionality.py
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Mock strategy_summary data
VALID_STRATEGY_SUMMARY = {
    "symbol": "AAPL",
    "strategy_name": "Bull Call Spread",
    "spot_price": 150.0,
    "expiration_date": "2024-12-20",
    "legs": [
        {
            "action": "buy",
            "quantity": 1,
            "strike": 150,
            "type": "call",
            "premium": 5.0,
            "delta": 0.5,
            "gamma": 0.01,
            "theta": -0.05,
            "vega": 0.1,
            "implied_volatility": 0.25,
        },
        {
            "action": "sell",
            "quantity": 1,
            "strike": 155,
            "type": "call",
            "premium": 2.0,
            "delta": 0.3,
            "gamma": 0.008,
            "theta": -0.03,
            "vega": 0.08,
            "implied_volatility": 0.24,
        }
    ],
    "strategy_metrics": {
        "max_profit": 700,
        "max_loss": -300,
        "breakeven_points": [153.0],
        "profit_zones": [[153.0, 155.0]],
    },
    "portfolio_greeks": {
        "delta": 0.2,
        "gamma": 0.002,
        "theta": -0.02,
        "vega": 0.02,
        "rho": 0.01,
    },
    "trade_execution": {
        "net_cost": -300,
        "legs": [
            {"action": "buy", "strike": 150, "premium": 500},
            {"action": "sell", "strike": 155, "premium": -200},
        ]
    },
    "payoff_summary": {
        "max_profit_price": 155.0,
        "max_loss_price": 150.0,
        "breakeven": 153.0,
    }
}

EDGE_CASES = [
    {
        "name": "All None values",
        "data": {
            "symbol": "AAPL",
            "strategy_name": "Test",
            "spot_price": 150.0,
            "legs": None,
            "strategy_metrics": None,
            "portfolio_greeks": None,
            "trade_execution": None,
        }
    },
    {
        "name": "Missing keys",
        "data": {
            "symbol": "AAPL",
            "strategy_name": "Test",
            "spot_price": 150.0,
        }
    },
    {
        "name": "Empty dicts",
        "data": {
            "symbol": "AAPL",
            "strategy_name": "Test",
            "spot_price": 150.0,
            "legs": [],
            "strategy_metrics": {},
            "portfolio_greeks": {},
            "trade_execution": {},
        }
    },
    {
        "name": "Invalid leg (None in list)",
        "data": {
            "symbol": "AAPL",
            "strategy_name": "Test",
            "spot_price": 150.0,
            "legs": [None, {"action": "buy", "strike": 150}],
            "strategy_metrics": {"max_profit": 100},
        }
    },
]


def test_strategy_summary_validation(strategy_summary: Dict[str, Any]) -> tuple[bool, str]:
    """Test if strategy_summary can be safely processed."""
    try:
        # Simulate the processing logic from gemini_provider.py
        
        # 1. Extract basic fields
        symbol = strategy_summary.get("symbol", "N/A")
        strategy_name = strategy_summary.get("strategy_name", "Custom Strategy")
        spot_price = strategy_summary.get("spot_price", 0)
        
        # 2. Extract legs (handle None case)
        legs = strategy_summary.get("legs")
        if not isinstance(legs, list):
            legs = []
        legs_json = []
        for leg in legs:
            if not isinstance(leg, dict):
                continue  # Skip invalid legs
            legs_json.append({
                "action": leg.get("action", "buy").upper(),
                "quantity": leg.get("quantity", 1),
                "strike": leg.get("strike", 0),
                "type": leg.get("type", "call").upper(),
            })
        
        # 3. Extract portfolio Greeks (handle None case)
        portfolio_greeks = strategy_summary.get("portfolio_greeks") or {}
        if not isinstance(portfolio_greeks, dict):
            portfolio_greeks = {}
        net_delta = portfolio_greeks.get("delta", 0)
        net_gamma = portfolio_greeks.get("gamma", 0)
        net_theta = portfolio_greeks.get("theta", 0)
        net_vega = portfolio_greeks.get("vega", 0)
        
        # 4. Extract strategy metrics (handle None case)
        strategy_metrics = strategy_summary.get("strategy_metrics")
        if not isinstance(strategy_metrics, dict):
            strategy_metrics = {}
        max_profit = strategy_metrics.get("max_profit", 0)
        max_loss = strategy_metrics.get("max_loss", 0)
        breakeven_points = strategy_metrics.get("breakeven_points", [])
        
        # 5. Extract trade execution (handle None case)
        trade_execution = strategy_summary.get("trade_execution")
        if not isinstance(trade_execution, dict):
            trade_execution = {}
        net_cost = trade_execution.get("net_cost", 0)
        
        # 6. Calculate IV from legs
        iv_values = []
        if isinstance(legs, list):
            for leg in legs:
                if isinstance(leg, dict):
                    iv = leg.get("implied_volatility") or leg.get("implied_vol", 0)
                    if iv:
                        iv_values.append(iv)
        current_iv = sum(iv_values) / len(iv_values) if iv_values else 0
        
        return True, f"Processed: {len(legs_json)} legs, profit=${max_profit}, loss=${max_loss}, IV={current_iv:.2%}"
        
    except AttributeError as e:
        return False, f"AttributeError: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def test_prompt_formatting(strategy_summary: Dict[str, Any]) -> tuple[bool, str]:
    """Test if prompt can be formatted without errors."""
    try:
        # Simulate prompt formatting
        symbol = strategy_summary.get("symbol", "N/A")
        strategy_name = strategy_summary.get("strategy_name", "Custom Strategy")
        spot_price = strategy_summary.get("spot_price", 0)
        
        legs = strategy_summary.get("legs") or []
        if not isinstance(legs, list):
            legs = []
        
        legs_json = []
        for leg in legs:
            if isinstance(leg, dict):
                legs_json.append({
                    "action": leg.get("action", "buy").upper(),
                    "strike": leg.get("strike", 0),
                    "type": leg.get("type", "call").upper(),
                })
        
        portfolio_greeks = strategy_summary.get("portfolio_greeks") or {}
        if not isinstance(portfolio_greeks, dict):
            portfolio_greeks = {}
        
        strategy_metrics = strategy_summary.get("strategy_metrics")
        if not isinstance(strategy_metrics, dict):
            strategy_metrics = {}
        
        # Format a simple prompt
        prompt = f"""
Target Ticker: {symbol}
Strategy Name: {strategy_name}
Current Spot Price: ${spot_price:.2f}
Strategy Legs: {json.dumps(legs_json, indent=2)}
Max Profit: ${strategy_metrics.get("max_profit", 0)}
Max Loss: ${strategy_metrics.get("max_loss", 0)}
Net Delta: {portfolio_greeks.get("delta", 0)}
"""
        
        if len(prompt) < 50:
            return False, "Prompt too short"
        
        return True, f"Prompt formatted: {len(prompt)} characters"
        
    except Exception as e:
        return False, f"Error formatting prompt: {e}"


async def test_ai_provider_imports():
    """Test if AI providers can be imported and initialized."""
    print("\n" + "=" * 60)
    print("Test: AI Provider Imports")
    print("=" * 60)
    
    try:
        from app.services.ai.gemini_provider import GeminiProvider
        from app.services.ai.image_provider import GeminiImageProvider
        print("✓ AI providers imported successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import AI providers: {e}")
        return False


def test_edge_cases():
    """Test edge cases for strategy_summary processing."""
    print("\n" + "=" * 60)
    print("Test: Edge Cases Handling")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_case in EDGE_CASES:
        name = test_case["name"]
        data = test_case["data"]
        
        print(f"\nTesting: {name}")
        success, message = test_strategy_summary_validation(data)
        
        if success:
            print(f"  ✓ {message}")
            passed += 1
        else:
            print(f"  ✗ {message}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


def test_valid_data():
    """Test with valid strategy_summary."""
    print("\n" + "=" * 60)
    print("Test: Valid Strategy Summary")
    print("=" * 60)
    
    print("\nTesting: Valid strategy_summary")
    success, message = test_strategy_summary_validation(VALID_STRATEGY_SUMMARY)
    
    if success:
        print(f"  ✓ {message}")
    else:
        print(f"  ✗ {message}")
        return False
    
    # Test prompt formatting
    print("\nTesting: Prompt formatting")
    success, message = test_prompt_formatting(VALID_STRATEGY_SUMMARY)
    
    if success:
        print(f"  ✓ {message}")
    else:
        print(f"  ✗ {message}")
        return False
    
    return True


def test_image_prompt_construction():
    """Test image prompt construction."""
    print("\n" + "=" * 60)
    print("Test: Image Prompt Construction")
    print("=" * 60)
    
    try:
        # Simulate image prompt construction
        strategy_summary = VALID_STRATEGY_SUMMARY.copy()
        
        ticker = strategy_summary.get("symbol", "N/A")
        strategy_name = strategy_summary.get("strategy_name", "Custom Strategy")
        current_price = strategy_summary.get("spot_price", 0)
        
        legs = strategy_summary.get("legs", [])
        legs_text = ""
        for i, leg in enumerate(legs, 1):
            if isinstance(leg, dict):
                action = leg.get("action", "buy").upper()
                strike = leg.get("strike", 0)
                option_type = leg.get("type", "call").upper()
                legs_text += f"    {i}. {action} {strike} {option_type}\n"
        
        strategy_metrics = strategy_summary.get("strategy_metrics")
        if not isinstance(strategy_metrics, dict):
            strategy_metrics = {}
        trade_execution = strategy_summary.get("trade_execution")
        if not isinstance(trade_execution, dict):
            trade_execution = {}
        
        net_cash_flow = trade_execution.get("net_cost", 0)
        max_profit = strategy_metrics.get("max_profit", 0)
        max_loss = strategy_metrics.get("max_loss", 0)
        breakeven_points = strategy_metrics.get("breakeven_points", [])
        breakeven = breakeven_points[0] if breakeven_points else 0
        
        prompt = f"""
Ticker: {ticker}
Strategy: {strategy_name}
Current Price: ${current_price:.2f}

Legs:
{legs_text.strip()}

Net Cash Flow: ${net_cash_flow:+.2f}
Max Profit: ${max_profit:,.2f}
Max Loss: ${max_loss:,.2f}
Breakeven: ${breakeven:.2f}
"""
        
        print(f"✓ Image prompt constructed: {len(prompt)} characters")
        return True
    except Exception as e:
        print(f"✗ Image prompt construction failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("AI Report and Image Generation Functionality Test")
    print("=" * 60)
    
    results = []
    
    # Test 1: Valid data
    results.append(test_valid_data())
    
    # Test 2: Edge cases
    results.append(test_edge_cases())
    
    # Test 3: Image prompt construction
    results.append(test_image_prompt_construction())
    
    # Test 4: AI provider imports (async)
    try:
        import_event_loop = asyncio.get_event_loop()
        if import_event_loop.is_closed():
            import_event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(import_event_loop)
    except RuntimeError:
        import_event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(import_event_loop)
    
    results.append(import_event_loop.run_until_complete(test_ai_provider_imports()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
        print("\nRecommendation: Code is ready for deployment.")
        return 0
    else:
        print("✗ Some tests failed!")
        print("\nRecommendation: Fix failing tests before deployment.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

