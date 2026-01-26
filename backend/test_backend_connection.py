#!/usr/bin/env python3
"""Quick test script to verify backend API is working."""

import requests
import sys

def test_backend():
    """Test backend health and basic endpoints."""
    base_url = "http://localhost:5300"
    
    print("=" * 60)
    print("Testing ThetaMind Backend API")
    print("=" * 60)
    
    # Test 1: Health check
    print("\n1. Testing /health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ Health check passed: {response.json()}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Cannot connect to {base_url}")
        print("   💡 Make sure the backend is running:")
        print("      docker logs thetamind-backend")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 2: Root endpoint
    print("\n2. Testing / endpoint...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ Root endpoint OK: {response.json()}")
        else:
            print(f"   ⚠️  Root endpoint returned: {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  Root endpoint error: {e}")
    
    # Test 3: API docs
    print("\n3. Testing /docs endpoint...")
    try:
        response = requests.get(f"{base_url}/docs", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ API docs available at {base_url}/docs")
        else:
            print(f"   ⚠️  API docs returned: {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  API docs error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Backend is running and responding!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_backend()
    sys.exit(0 if success else 1)
