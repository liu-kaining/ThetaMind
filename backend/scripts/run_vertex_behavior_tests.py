#!/usr/bin/env python3
"""
Run Vertex AI behavior checks without pytest.
Requires backend deps (httpx, etc.). Run from backend env, e.g.:
  cd backend && poetry run python scripts/run_vertex_behavior_tests.py
  or from backend container: python scripts/run_vertex_behavior_tests.py
With pytest: cd backend && poetry run pytest tests/test_gemini_vertex_behavior.py -v
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Minimal env so Settings() can load when we import app
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-for-vertex-tests")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/thetamind")


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def main():
    ok = 0
    fail = 0

    captured = {"url": None, "payload": None}

    async def fake_post(url, *, headers=None, json=None, params=None, **kwargs):
        captured["url"] = url
        captured["payload"] = json
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(
            return_value={
                "candidates": [
                    {"content": {"parts": [{"text": "ok"}]}, "finishReason": "STOP"}
                ]
            }
        )
        return resp

    # Patch settings in gemini_provider so Vertex key + model use our test values
    from app.core import config
    from app.services.ai import gemini_provider as gp

    with patch.object(config.settings, "google_api_key", "AQ.test_vertex_key_placeholder"), \
         patch.object(config.settings, "ai_model_default", "gemini-3.0-pro-preview"), \
         patch.object(config.settings, "google_cloud_project", "test-project"), \
         patch.object(config.settings, "google_cloud_location", "us-central1"), \
         patch.object(config.settings, "ai_model_timeout", 60), \
         patch.object(gp, "httpx") as mock_httpx:
            client = AsyncMock()
            client.post = AsyncMock(side_effect=fake_post)
            mock_httpx.AsyncClient.return_value = client

            from app.services.ai.gemini_provider import GeminiProvider

            # 1. Init: location=us-central1 for gemini-3-pro-preview (Preview models)
            try:
                provider = GeminiProvider()
                assert provider.use_vertex_ai is True
                assert "locations/us-central1" in provider.vertex_ai_project_url
                assert provider.vertex_model_id == "gemini-3-pro-preview"
                print("[OK] Init: vertex_ai_project_url uses location=us-central1")
                ok += 1
            except Exception as e:
                print(f"[FAIL] Init: {e}")
                fail += 1

            # 2. Init: project URL path
            try:
                assert "projects/test-project" in provider.vertex_ai_project_url
                assert "publishers/google/models" in provider.vertex_ai_project_url
                print("[OK] Init: vertex_ai_project_url is project/location path")
                ok += 1
            except Exception as e:
                print(f"[FAIL] Init URL path: {e}")
                fail += 1

            # 3. _vertex_supports_system_instruction False for gemini-3-pro
            try:
                assert provider._vertex_supports_system_instruction() is False
                print("[OK] _vertex_supports_system_instruction() is False for gemini-3-pro-preview")
                ok += 1
            except Exception as e:
                print(f"[FAIL] system instruction support: {e}")
                fail += 1

            # 4. _call_vertex_ai: no systemInstruction in payload, uses project URL
            async def check_call_vertex_ai():
                await provider._call_vertex_ai("user prompt", system_prompt="system text")
                p = captured["payload"]
                u = captured["url"]
                assert "systemInstruction" not in p
                assert "system text" in p["contents"][0]["parts"][0]["text"]
                assert "user prompt" in p["contents"][0]["parts"][0]["text"]
                assert "projects/" in u and "locations/us-central1" in u
                assert "gemini-3-pro-preview:generateContent" in u

            try:
                run_async(check_call_vertex_ai())
                print("[OK] _call_vertex_ai: no systemInstruction in payload, uses project URL")
                ok += 1
            except Exception as e:
                print(f"[FAIL] _call_vertex_ai: {e}")
                fail += 1

            # 5. _call_gemini_with_search(use_search=False): no tools, project URL
            async def check_planning():
                await provider._call_gemini_with_search("planning prompt", use_search=False)
                p = captured["payload"]
                u = captured["url"]
                assert "tools" not in p
                assert "projects/" in u and "locations/us-central1" in u

            try:
                run_async(check_planning())
                print("[OK] _call_gemini_with_search(use_search=False): no tools, project URL")
                ok += 1
            except Exception as e:
                print(f"[FAIL] _call_gemini_with_search(use_search=False): {e}")
                fail += 1

            # 6. _call_gemini_with_search(use_search=True): has tools
            async def check_research():
                await provider._call_gemini_with_search("research prompt", use_search=True)
                p = captured["payload"]
                assert "tools" in p
                assert p["tools"] == [{"googleSearch": {}}]

            try:
                run_async(check_research())
                print("[OK] _call_gemini_with_search(use_search=True): has googleSearch tools")
                ok += 1
            except Exception as e:
                print(f"[FAIL] _call_gemini_with_search(use_search=True): {e}")
                fail += 1

            # 7. _call_gemini_with_search + system_prompt: no systemInstruction in payload
            async def check_system_prepended():
                await provider._call_gemini_with_search(
                    "user text", use_search=False, system_prompt="system part"
                )
                p = captured["payload"]
                assert "systemInstruction" not in p
                assert "system part" in p["contents"][0]["parts"][0]["text"]
                assert "user text" in p["contents"][0]["parts"][0]["text"]

            try:
                run_async(check_system_prepended())
                print("[OK] _call_gemini_with_search + system_prompt: prepended, no systemInstruction")
                ok += 1
            except Exception as e:
                print(f"[FAIL] system_prompt prepended: {e}")
                fail += 1

    print()
    print(f"Result: {ok} passed, {fail} failed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
