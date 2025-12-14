#!/usr/bin/env python3
"""Test script for Gemini image generation functionality."""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ai.image_provider import get_image_provider
from app.core.config import settings


async def test_image_generation():
    """Test image generation with a simple prompt."""
    print("=" * 60)
    print("Testing Gemini Image Generation")
    print("=" * 60)
    
    # Check configuration
    print(f"\n1. Configuration Check:")
    print(f"   - AI Provider: {settings.ai_provider}")
    print(f"   - AI Image Model: {settings.ai_image_model}")
    print(f"   - Google API Key: {'Set' if settings.google_api_key else 'NOT SET'}")
    if settings.google_api_key:
        key_prefix = settings.google_api_key[:10]
        key_type = "Vertex AI" if settings.google_api_key.startswith("AQ.") else "Generative API"
        print(f"   - API Key prefix: {key_prefix}... ({key_type})")
    
    # Test provider initialization
    print(f"\n2. Provider Initialization:")
    try:
        provider = get_image_provider()
        print(f"   ✓ Provider initialized: {type(provider).__name__}")
        print(f"   - Model name: {provider.model_name}")
        print(f"   - API key configured: {bool(provider.api_key)}")
    except Exception as e:
        print(f"   ✗ Failed to initialize provider: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test prompt construction
    print(f"\n3. Prompt Construction Test:")
    try:
        strategy_data = {
            "symbol": "AAPL",
            "strategy_name": "Test Long Call",
            "current_price": 150.0,
            "legs": [
                {
                    "action": "buy",
                    "type": "call",
                    "strike": 155,
                    "role": "Long Call"
                }
            ]
        }
        metrics = {
            "net_cash_flow": -500.0,
            "max_profit": 1000.0,
            "max_loss": -500.0,
            "breakeven": 160.0,
            "margin": 0
        }
        
        prompt = provider.construct_image_prompt(strategy_data, metrics)
        print(f"   ✓ Prompt constructed successfully")
        print(f"   - Prompt length: {len(prompt)} characters")
        print(f"   - First 200 chars: {prompt[:200]}...")
    except Exception as e:
        print(f"   ✗ Failed to construct prompt: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test API call with simple prompt first
    print(f"\n4. API Call Test (Simple Prompt):")
    print(f"   ⚠️  This will attempt to call Gemini API...")
    try:
        # Use a simple test prompt first
        test_prompt = "Create a simple test image: a red circle on white background"
        print(f"   - Calling Gemini API with test prompt...")
        print(f"   - This may take 30-60 seconds...")
        
        image_base64 = await provider.generate_chart(test_prompt)
        
        if image_base64:
            print(f"   ✓ API call successful!")
            print(f"   - Image data length: {len(image_base64)} characters")
            print(f"   - Image size (approx): {len(image_base64) * 3 // 4 / 1024:.2f} KB")
            
            # Save test image to file for verification
            import base64
            image_bytes = base64.b64decode(image_base64)
            test_image_path = "/tmp/test_gemini_image.png"
            with open(test_image_path, "wb") as f:
                f.write(image_bytes)
            print(f"   - Test image saved to: {test_image_path}")
            
            return True
        else:
            print(f"   ✗ API returned empty result")
            return False
            
    except Exception as e:
        print(f"   ✗ API call failed: {e}")
        print(f"   - Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\nStarting Gemini image generation test...\n")
    success = asyncio.run(test_image_generation())
    print("\n" + "=" * 60)
    if success:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed. Check the output above for details.")
    print("=" * 60 + "\n")
    sys.exit(0 if success else 1)

