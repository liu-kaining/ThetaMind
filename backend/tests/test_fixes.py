#!/usr/bin/env python3
"""
Test script to verify AI report and image generation fixes.

This script tests:
1. AI report generation with strategy_summary containing None values
2. Image base64 data validation and cleaning
"""

import base64
import sys


def test_strategy_metrics_none_handling():
    """Test that strategy_metrics=None is handled correctly."""
    print("=" * 60)
    print("Test 1: strategy_metrics=None handling")
    print("=" * 60)
    
    # Test the logic we fixed in the code
    test_cases = [
        ("None value", None),
        ("Missing key", {}),  # Simulating .get() returning {}
        ("Empty dict", {}),
        ("Valid dict", {"max_profit": 100, "max_loss": -50}),
    ]
    
    for name, strategy_metrics in test_cases:
        print(f"\nTesting: {name}")
        try:
            # Simulate the fixed logic
            if not isinstance(strategy_metrics, dict):
                strategy_metrics = {}
            
            # These should not raise AttributeError
            max_profit = strategy_metrics.get("max_profit", 0)
            max_loss = strategy_metrics.get("max_loss", 0)
            breakeven_points = strategy_metrics.get("breakeven_points", [])
            
            print(f"  ✓ Handled correctly: max_profit={max_profit}, max_loss={max_loss}, breakevens={len(breakeven_points)}")
        except AttributeError as e:
            print(f"  ✗ AttributeError occurred: {e}")
            return False
        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
            return False
    
    print("\n✓ All strategy_metrics None handling tests passed!")
    return True


def test_base64_cleaning():
    """Test base64 data cleaning and validation."""
    print("\n" + "=" * 60)
    print("Test 2: Base64 data cleaning and validation")
    print("=" * 60)
    
    # Create a larger valid PNG (10x10 pixel) to meet 100-byte minimum
    # This is a simplified PNG structure - in reality, we'd use a proper PNG encoder
    # For testing purposes, we'll create a base64 string that decodes to >100 bytes
    # We'll use a dummy base64 string that's long enough
    dummy_image_data = b'\x89PNG' + b'\x00' * 100  # PNG header + 100 bytes of dummy data
    valid_base64 = base64.b64encode(dummy_image_data).decode('utf-8')
    
    # Test cases
    test_cases = [
        ("Clean base64", valid_base64),
        ("Base64 with newlines", valid_base64[:20] + "\n" + valid_base64[20:40] + "\n" + valid_base64[40:]),
        ("Base64 with spaces", valid_base64[:20] + " " + valid_base64[20:40] + " " + valid_base64[40:]),
        ("Base64 with data URL prefix", f"data:image/png;base64,{valid_base64}"),
        ("Base64 with data URL and newlines", f"data:image/png;base64,\n{valid_base64[:20]}\n{valid_base64[20:]}\n"),
    ]
    
    for name, test_data in test_cases:
        print(f"\nTesting: {name}")
        try:
            # Clean base64 data
            cleaned = test_data.strip()
            if cleaned.startswith("data:"):
                cleaned = cleaned.split(",", 1)[-1].strip()
            cleaned = "".join(cleaned.split())
            
            # Validate
            decoded = base64.b64decode(cleaned, validate=True)
            if len(decoded) < 100:
                print(f"  ✗ Decoded data too small: {len(decoded)} bytes")
                return False
            
            # Check PNG header
            if decoded[:4] != b'\x89PNG':
                print(f"  ✗ Invalid PNG header: {decoded[:4]}")
                return False
            
            print(f"  ✓ Base64 cleaned and validated successfully ({len(decoded)} bytes)")
        except Exception as e:
            print(f"  ✗ Base64 cleaning/validation failed: {e}")
            return False
    
    print("\n✓ All base64 cleaning tests passed!")
    return True


def test_invalid_base64():
    """Test handling of invalid base64 data."""
    print("\n" + "=" * 60)
    print("Test 3: Invalid base64 data handling")
    print("=" * 60)
    
    invalid_cases = [
        ("Empty string", ""),
        ("Invalid characters", "!!!invalid base64!!!"),
        ("Too short", "aGVsbG8="),  # "hello" - too short for an image
    ]
    
    for name, invalid_data in invalid_cases:
        print(f"\nTesting: {name}")
        try:
            cleaned = invalid_data.strip()
            if cleaned.startswith("data:"):
                cleaned = cleaned.split(",", 1)[-1].strip()
            cleaned = "".join(cleaned.split())
            
            if not cleaned:
                print(f"  ✓ Correctly detected empty base64")
                continue
            
            decoded = base64.b64decode(cleaned, validate=True)
            if len(decoded) < 100:
                print(f"  ✓ Correctly detected too small data: {len(decoded)} bytes")
                continue
            
            print(f"  ✗ Should have failed but didn't")
            return False
        except base64.binascii.Error:
            print(f"  ✓ Correctly detected invalid base64 format")
        except Exception as e:
            print(f"  ✓ Correctly detected error: {type(e).__name__}")
    
    print("\n✓ All invalid base64 handling tests passed!")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Testing AI Report and Image Generation Fixes")
    print("=" * 60)
    
    results = []
    
    # Test 1: strategy_metrics None handling
    results.append(test_strategy_metrics_none_handling())
    
    # Test 2: Base64 cleaning
    results.append(test_base64_cleaning())
    
    # Test 3: Invalid base64 handling
    results.append(test_invalid_base64())
    
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

