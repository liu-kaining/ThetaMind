#!/usr/bin/env python3
"""
Simple HTTP test for Gemini API.
"""

import os
import sys
import json
import requests

def test_gemini_http():
    """Test Gemini API using HTTP requests."""
    
    print("=" * 60)
    print("Gemini API HTTP Test")
    print("=" * 60)
    print()
    
    # 1. Get API key
    print("1. Reading API key...")
    api_key = os.getenv("GOOGLE_API_KEY", "")
    
    if not api_key:
        # Try reading from .env
        try:
            env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.startswith("GOOGLE_API_KEY="):
                            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
        except Exception as e:
            print(f"   ⚠️  Error reading .env: {e}")
    
    if not api_key:
        print("   ❌ GOOGLE_API_KEY not found")
        return False
    
    masked_key = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 14 else "***"
    print(f"   ✅ API Key found: {masked_key}")
    print(f"   API Key length: {len(api_key)} characters")
    print(f"   API Key starts with: {api_key[:5] if len(api_key) >= 5 else api_key}")
    
    # Check if it looks like a Gemini API key (usually starts with AIza)
    if not api_key.startswith("AIza"):
        print(f"   ⚠️  Warning: API key doesn't start with 'AIza' (typical Gemini API key format)")
    print()
    
    # 2. Test API endpoint (Vertex AI format)
    model_name = "gemini-2.5-flash-lite"
    url = f"https://aiplatform.googleapis.com/v1/publishers/google/models/{model_name}:streamGenerateContent?key={api_key}"
    
    print(f"2. Testing Gemini API endpoint (Vertex AI)...")
    print(f"   URL: {url.split('?')[0]}... (API key in query)")
    print(f"   Model: {model_name}")
    print()
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": "Say 'Hello from Gemini API' in exactly 4 words."
                    }
                ]
            }
        ]
    }
    
    print("3. Sending request...")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"   Status Code: {response.status_code}")
        print()
        
        if response.status_code == 200:
            # streamGenerateContent returns streaming response, need to handle it
            response_text = response.text
            print(f"   Response length: {len(response_text)} bytes")
            
            # streamGenerateContent returns streaming format as JSON array
            # Response is an array of chunks
            print("   Parsing streaming response (JSON array format)...")
            texts = []
            
            try:
                chunks = json.loads(response_text)
                # chunks is an array of response objects
                if isinstance(chunks, list):
                    for chunk in chunks:
                        if "candidates" in chunk and len(chunk["candidates"]) > 0:
                            candidate = chunk["candidates"][0]
                            if "content" in candidate and "parts" in candidate["content"]:
                                for part in candidate["content"]["parts"]:
                                    if "text" in part:
                                        text = part["text"]
                                        if text:
                                            texts.append(text)
                elif isinstance(chunks, dict):
                    # Single response object
                    if "candidates" in chunks and len(chunks["candidates"]) > 0:
                        candidate = chunks["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            for part in candidate["content"]["parts"]:
                                if "text" in part:
                                    text = part["text"]
                                    if text:
                                        texts.append(text)
            except json.JSONDecodeError as e:
                print(f"   ❌ Failed to parse JSON: {e}")
                print(f"   Response preview: {response_text[:500]}")
                return False
            
            if texts:
                full_text = "".join(texts)
                print("4. ✅ SUCCESS! Gemini API is working!")
                print()
                print("   Response:")
                print(f"   {full_text.strip()}")
                print()
                print("=" * 60)
                print("✅ All tests passed!")
                print("=" * 60)
                return True
            else:
                print("   ❌ Could not extract text from streaming response")
                print(f"   Response preview: {response_text[:500]}")
                return False
        else:
            print(f"   ❌ Request failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            
            # Provide helpful error messages
            if response.status_code == 401:
                print("   💡 Authentication failed. Check if your API key is valid.")
            elif response.status_code == 403:
                print("   💡 Permission denied. Check if your API key has access to Gemini API.")
            elif response.status_code == 429:
                print("   💡 Rate limit exceeded. Please try again later.")
            elif response.status_code == 400:
                print("   💡 Bad request. Check the request format.")
            
            return False
            
    except requests.exceptions.Timeout:
        print("   ❌ Request timed out (>30s)")
        return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"   ❌ Failed to parse JSON response: {e}")
        print(f"   Response: {response.text[:500]}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = test_gemini_http()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

