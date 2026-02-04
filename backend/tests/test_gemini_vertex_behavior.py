"""
Unit tests for GeminiProvider Vertex AI behavior.

Verifies:
- Vertex URL: all calls use project/location URL (vertex_ai_project_url), not publisher-only.
- Preview models (gemini-3-pro-preview): v1beta1 API + us-central1 (v1/global causes 400/404).
- _call_vertex_ai: may send systemInstruction when supported; generationConfig always sent (no thinkingConfig).
- _call_gemini_with_search: system prompt prepended to user prompt (max compatibility); generationConfig always sent; no thinkingConfig; use_search=False has no tools; use_search=True has tools.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_settings_vertex():
    """Settings for Vertex AI key and gemini-3.0-pro-preview."""
    with patch("app.services.ai.gemini_provider.settings") as m:
        m.google_api_key = "AQ.test_vertex_key_placeholder"
        m.ai_model_default = "gemini-3.0-pro-preview"
        m.google_cloud_project = "test-project"
        m.google_cloud_location = "us-central1"  # preview uses us-central1 + v1beta1
        m.ai_model_timeout = 60
        yield m


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient.post to capture URL and payload, return success."""
    captured = {"url": None, "payload": None, "params": None}

    async def fake_post(url, *, headers=None, json=None, params=None, **kwargs):
        captured["url"] = url
        captured["payload"] = json
        captured["params"] = params
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(
            return_value={
                "candidates": [
                    {
                        "content": {"parts": [{"text": "ok"}]},
                        "finishReason": "STOP",
                    }
                ]
            }
        )
        resp.status_code = 200
        return resp

    with patch("app.services.ai.gemini_provider.httpx") as mock_httpx:
        client = AsyncMock()
        client.post = AsyncMock(side_effect=fake_post)
        mock_httpx.AsyncClient.return_value = client
        yield captured


class TestVertexInit:
    """Vertex AI init: URL and location."""

    def test_vertex_project_url_uses_v1beta1_us_central1_for_gemini_3_pro_preview(
        self, mock_settings_vertex, mock_httpx_client
    ):
        """Preview model must use v1beta1 and us-central1 (v1/global causes 400/404)."""
        from app.services.ai.gemini_provider import GeminiProvider

        provider = GeminiProvider()
        assert provider.use_vertex_ai is True
        assert "v1beta1" in provider.vertex_ai_project_url
        assert "locations/us-central1" in provider.vertex_ai_project_url
        assert provider.vertex_model_id == "gemini-3-pro-preview"

    def test_vertex_project_url_contains_project_and_models(self, mock_settings_vertex, mock_httpx_client):
        """vertex_ai_project_url must be project/location path."""
        from app.services.ai.gemini_provider import GeminiProvider

        provider = GeminiProvider()
        assert "projects/test-project" in provider.vertex_ai_project_url
        assert "publishers/google/models" in provider.vertex_ai_project_url
        assert provider.vertex_ai_project_url.endswith("/publishers/google/models")


class TestVertexSystemInstruction:
    """systemInstruction support and payload."""

    def test_vertex_supports_system_instruction_true_for_gemini_3_pro(self, mock_settings_vertex, mock_httpx_client):
        """_vertex_supports_system_instruction is True for gemini-3-pro-preview (Gemini 3 Pro doc 功能/系统指令)."""
        from app.services.ai.gemini_provider import GeminiProvider

        provider = GeminiProvider()
        assert provider._vertex_supports_system_instruction() is True

    @pytest.mark.asyncio
    async def test_call_vertex_ai_sends_system_instruction_in_payload(
        self, mock_settings_vertex, mock_httpx_client
    ):
        """_call_vertex_ai sends systemInstruction in payload for gemini-3-pro-preview when provided."""
        from app.services.ai.gemini_provider import GeminiProvider

        provider = GeminiProvider()
        await provider._call_vertex_ai("user prompt", system_prompt="system text")
        payload = mock_httpx_client["payload"]
        assert "systemInstruction" in payload
        assert payload["systemInstruction"]["parts"][0]["text"] == "system text"
        assert payload["contents"][0]["parts"][0]["text"] == "user prompt"

    @pytest.mark.asyncio
    async def test_call_vertex_ai_uses_project_url(self, mock_settings_vertex, mock_httpx_client):
        """_call_vertex_ai must use vertex_ai_project_url (project/location), not publisher-only."""
        from app.services.ai.gemini_provider import GeminiProvider

        provider = GeminiProvider()
        await provider._call_vertex_ai("hello")
        url = mock_httpx_client["url"]
        assert "projects/" in url
        assert "v1beta1" in url
        assert "locations/us-central1" in url
        assert "gemini-3-pro-preview:generateContent" in url
        assert url.startswith("https://aiplatform.googleapis.com/v1beta1/projects/")


class TestCallGeminiWithSearch:
    """_call_gemini_with_search: URL and payload (tools / systemInstruction)."""

    @pytest.mark.asyncio
    async def test_with_search_false_uses_project_url_no_tools(
        self, mock_settings_vertex, mock_httpx_client
    ):
        """use_search=False must use project URL and must NOT include tools in payload."""
        from app.services.ai.gemini_provider import GeminiProvider

        provider = GeminiProvider()
        await provider._call_gemini_with_search("planning prompt", use_search=False)
        url = mock_httpx_client["url"]
        payload = mock_httpx_client["payload"]
        assert "projects/" in url and "v1beta1" in url and "locations/us-central1" in url
        assert "gemini-3-pro-preview:generateContent" in url
        assert "tools" not in payload
        assert "generationConfig" in payload
        assert "temperature" in payload["generationConfig"]

    @pytest.mark.asyncio
    async def test_with_search_true_includes_tools(self, mock_settings_vertex, mock_httpx_client):
        """use_search=True must include tools with googleSearch."""
        from app.services.ai.gemini_provider import GeminiProvider

        provider = GeminiProvider()
        await provider._call_gemini_with_search("research prompt", use_search=True)
        payload = mock_httpx_client["payload"]
        assert "tools" in payload
        assert payload["tools"] == [{"googleSearch": {}}]
        assert "generationConfig" in payload

    @pytest.mark.asyncio
    async def test_with_search_prepends_system_prompt_no_system_instruction_in_payload(
        self, mock_settings_vertex, mock_httpx_client
    ):
        """_call_gemini_with_search prepends system prompt (max compatibility); no systemInstruction in payload."""
        from app.services.ai.gemini_provider import GeminiProvider

        provider = GeminiProvider()
        await provider._call_gemini_with_search(
            "user text", use_search=False, system_prompt="system part"
        )
        payload = mock_httpx_client["payload"]
        assert "systemInstruction" not in payload
        text = payload["contents"][0]["parts"][0]["text"]
        assert "system part" in text
        assert "user text" in text
        assert "System Instruction:" in text
        assert "User Query:" in text


class TestVertexNoThinkingConfig:
    """Safe config: no thinkingConfig sent (Pro models may reject it with 400)."""

    @pytest.mark.asyncio
    async def test_call_vertex_ai_has_generation_config_no_thinking_config(
        self, mock_settings_vertex, mock_httpx_client
    ):
        """_call_vertex_ai sends generationConfig (required) but not thinkingConfig."""
        from app.services.ai.gemini_provider import GeminiProvider

        provider = GeminiProvider()
        await provider._call_vertex_ai("hello")
        payload = mock_httpx_client["payload"]
        assert "generationConfig" in payload
        assert "thinkingConfig" not in payload["generationConfig"]

    @pytest.mark.asyncio
    async def test_call_gemini_with_search_has_generation_config_no_thinking_config(
        self, mock_settings_vertex, mock_httpx_client
    ):
        """_call_gemini_with_search sends generationConfig but not thinkingConfig."""
        from app.services.ai.gemini_provider import GeminiProvider

        provider = GeminiProvider()
        await provider._call_gemini_with_search("planning", use_search=False)
        payload = mock_httpx_client["payload"]
        assert "generationConfig" in payload
        assert "temperature" in payload["generationConfig"]
        assert "thinkingConfig" not in payload["generationConfig"]
