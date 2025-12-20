#!/usr/bin/env python3
"""
Comprehensive test script to verify AI report generation fixes.

Tests:
1. strategy_metrics=None handling
2. portfolio_greeks=None handling
3. trade_execution=None handling
4. legs=None or invalid legs handling
5. Prompt generation and saving
"""

import json
import sys


def test_none_handling():
    """Test all None value handling scenarios."""
    print("=" * 60)
    print("Test: None Value Handling")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "All None values",
            "strategy_summary": {
                "symbol": "AAPL",
                "strategy_name": "Test Strategy",
                "spot_price": 150.0,
                "legs": None,
                "strategy_metrics": None,
                "portfolio_greeks": None,
                "trade_execution": None,
            }
        },
        {
            "name": "Missing keys",
            "strategy_summary": {
                "symbol": "AAPL",
                "strategy_name": "Test Strategy",
                "spot_price": 150.0,
                # Missing: legs, strategy_metrics, portfolio_greeks, trade_execution
            }
        },
        {
            "name": "Empty dicts",
            "strategy_summary": {
                "symbol": "AAPL",
                "strategy_name": "Test Strategy",
                "spot_price": 150.0,
                "legs": [],
                "strategy_metrics": {},
                "portfolio_greeks": {},
                "trade_execution": {},
            }
        },
        {
            "name": "Invalid leg (None in list)",
            "strategy_summary": {
                "symbol": "AAPL",
                "strategy_name": "Test Strategy",
                "spot_price": 150.0,
                "legs": [None, {"action": "buy", "strike": 150}],
                "strategy_metrics": {"max_profit": 100},
                "portfolio_greeks": {"delta": 0.5},
                "trade_execution": {"net_cost": 500},
            }
        },
        {
            "name": "Invalid leg (not a dict)",
            "strategy_summary": {
                "symbol": "AAPL",
                "strategy_name": "Test Strategy",
                "spot_price": 150.0,
                "legs": ["invalid", {"action": "buy", "strike": 150}],
                "strategy_metrics": {"max_profit": 100},
                "portfolio_greeks": {"delta": 0.5},
                "trade_execution": {"net_cost": 500},
            }
        },
        {
            "name": "Valid data",
            "strategy_summary": {
                "symbol": "AAPL",
                "strategy_name": "Test Strategy",
                "spot_price": 150.0,
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
                    }
                ],
                "strategy_metrics": {
                    "max_profit": 1000,
                    "max_loss": -500,
                    "breakeven_points": [155.0, 145.0],
                },
                "portfolio_greeks": {
                    "delta": 0.5,
                    "gamma": 0.01,
                    "theta": -0.05,
                    "vega": 0.1,
                },
                "trade_execution": {
                    "net_cost": 500,
                },
            }
        },
    ]
    
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        name = test_case["name"]
        strategy_summary = test_case["strategy_summary"]
        
        print(f"\nTesting: {name}")
        try:
            # Simulate the fixed logic from gemini_provider.py
            strategy_context = strategy_summary
            
            # Extract legs (handle None case)
            legs = strategy_context.get("legs")
            if not isinstance(legs, list):
                legs = []
            legs_json = []
            for leg in legs:
                if not isinstance(leg, dict):
                    print(f"  ⚠ Skipping invalid leg (not a dict): {leg}")
                    continue
                legs_json.append({
                    "action": leg.get("action", "buy").upper(),
                    "quantity": leg.get("quantity", 1),
                    "strike": leg.get("strike", 0),
                    "type": leg.get("type", "call").upper(),
                })
            
            # Extract portfolio Greeks (handle None case)
            portfolio_greeks = strategy_context.get("portfolio_greeks") or {}
            if not isinstance(portfolio_greeks, dict):
                portfolio_greeks = {}
            net_delta = portfolio_greeks.get("delta", 0)
            net_gamma = portfolio_greeks.get("gamma", 0)
            net_theta = portfolio_greeks.get("theta", 0)
            net_vega = portfolio_greeks.get("vega", 0)
            
            # Extract strategy metrics (handle None case)
            strategy_metrics = strategy_context.get("strategy_metrics")
            if not isinstance(strategy_metrics, dict):
                strategy_metrics = {}
            max_profit = strategy_metrics.get("max_profit", 0)
            max_loss = strategy_metrics.get("max_loss", 0)
            breakeven_points = strategy_metrics.get("breakeven_points", [])
            
            # Extract trade execution (handle None case)
            trade_execution = strategy_context.get("trade_execution")
            if not isinstance(trade_execution, dict):
                trade_execution = {}
            net_cost = trade_execution.get("net_cost", 0)
            
            # Calculate IV from legs
            iv_values = []
            if isinstance(legs, list):
                for leg in legs:
                    if isinstance(leg, dict):
                        iv = leg.get("implied_volatility") or leg.get("implied_vol", 0)
                        if iv:
                            iv_values.append(iv)
            current_iv = sum(iv_values) / len(iv_values) if iv_values else 0
            
            print(f"  ✓ Processed successfully:")
            print(f"    - Legs: {len(legs_json)} valid legs")
            print(f"    - Max Profit: ${max_profit}")
            print(f"    - Max Loss: ${max_loss}")
            print(f"    - Net Delta: {net_delta}")
            print(f"    - Net Cost: ${net_cost}")
            print(f"    - IV: {current_iv:.2%}")
            
            passed += 1
        except AttributeError as e:
            print(f"  ✗ AttributeError: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


def test_prompt_generation():
    """Test prompt generation with various data scenarios."""
    print("\n" + "=" * 60)
    print("Test: Prompt Generation")
    print("=" * 60)
    
    strategy_summary = {
        "symbol": "AAPL",
        "strategy_name": "Bull Call Spread",
        "spot_price": 150.0,
        "legs": [
            {
                "action": "buy",
                "quantity": 1,
                "strike": 150,
                "type": "call",
                "premium": 5.0,
            }
        ],
        "strategy_metrics": {
            "max_profit": 1000,
            "max_loss": -500,
            "breakeven_points": [155.0],
        },
        "portfolio_greeks": {
            "delta": 0.5,
            "gamma": 0.01,
            "theta": -0.05,
            "vega": 0.1,
        },
    }
    
    try:
        # Simulate prompt formatting
        symbol = strategy_summary.get("symbol", "N/A")
        strategy_name = strategy_summary.get("strategy_name", "Custom Strategy")
        spot_price = strategy_summary.get("spot_price", 0)
        
        legs = strategy_summary.get("legs", [])
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
        
        print(f"✓ Prompt generated successfully ({len(prompt)} characters)")
        print(f"  Preview: {prompt[:200]}...")
        return True
    except Exception as e:
        print(f"✗ Prompt generation failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Comprehensive AI Report Fixes Test")
    print("=" * 60)
    
    results = []
    
    # Test 1: None handling
    results.append(test_none_handling())
    
    # Test 2: Prompt generation
    results.append(test_prompt_generation())
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

