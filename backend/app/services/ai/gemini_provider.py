"""Google Gemini AI provider implementation.

Supports both Generative Language API (AIza... keys) and Vertex AI (AQ.Ab... keys).
"""

import asyncio
import json
import logging
import re
from typing import Any

import httpx
from pybreaker import CircuitBreaker, CircuitBreakerError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Try to import google.generativeai (only needed for Generative Language API)
try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig
    HAS_GENAI_SDK = True
except ImportError:
    HAS_GENAI_SDK = False
    genai = None
    GenerationConfig = None

from app.core.config import settings
from app.services.ai.base import BaseAIProvider
from app.services.config_service import config_service

logger = logging.getLogger(__name__)

# Default prompt templates (fallback if config not set)
DEFAULT_REPORT_PROMPT_TEMPLATE = """You are a senior Wall Street options strategist. Analyze this strategy and provide a comprehensive report in Markdown.

**Strategy Context:**
{strategy_data}

**Market Data (ATM ±15%):**
{filtered_chain}

**Requirements:**
1. Strategy Overview: Explain the mechanics.
2. Risk Analysis: Highlight Max Loss, Vega risk, and Gamma risk.
3. Break-even Points: Calculate exact price points.
4. Market Sentiment: Use Google Search to find recent news about the underlying asset.
5. Verdict: Bullish, Bearish, or Neutral?

**Format:**
Return pure Markdown. Do not include JSON.
"""

DEFAULT_DAILY_PICKS_PROMPT = """Generate 3 distinct US stock option strategy recommendations for today based on current market pre-market conditions.

**Criteria:**
- Look for stocks with high IV Rank or recent news catalysts (Earnings, Fed, etc).
- Use Google Search to validate the opportunity.

**Output Format:**
Return a JSON Array of objects. Each object must follow this schema:
[
  {{
    "symbol": "TSLA",
    "strategy_type": "Iron Condor",
    "direction": "Neutral",
    "rationale": "High IV before earnings...",
    "risk_level": "High",
    "target_expiration": "2024-06-21"
  }}
]
"""

# Circuit breaker for Gemini API (same pattern as Tiger service)
gemini_circuit_breaker = CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
)


class GeminiProvider(BaseAIProvider):
    """Gemini 3 Pro Preview provider for AI analysis.
    
    Supports both:
    - Generative Language API (API keys starting with "AIza...")
    - Vertex AI (API keys starting with "AQ.Ab...")
    """

    def __init__(self) -> None:
        """Initialize Gemini client.
        
        Automatically detects API key format and uses appropriate endpoint:
        - Vertex AI key (AQ.Ab...): Uses Vertex AI HTTP endpoint
        - Generative Language API key (AIza...): Uses google.generativeai SDK
        """
        # Ensure API key is configured
        if not settings.google_api_key:
            logger.error("Google API key is not configured. Gemini features will not work.")
            raise ValueError("Google API key is required for Gemini provider")
        
        self.api_key = settings.google_api_key
        self.model_name = settings.ai_model_default
        
        # Detect API key type
        if self.api_key.startswith("AQ."):
            # Vertex AI API key - use HTTP endpoint
            self.use_vertex_ai = True
            self.vertex_ai_base_url = "https://aiplatform.googleapis.com/v1"
            self.model = None  # Not using SDK model
            logger.info(f"Detected Vertex AI API key. Using Vertex AI endpoint for model: {self.model_name}")
        elif self.api_key.startswith("AIza") and HAS_GENAI_SDK:
            # Generative Language API key - use SDK
            self.use_vertex_ai = False
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(model_name=self.model_name)
                logger.info(f"Detected Generative Language API key. Using SDK for model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini SDK model: {e}")
                self.model = None
                logger.warning("Gemini provider initialized but model is unavailable. AI features will be disabled.")
        else:
            # Unknown format or SDK not available
            if not HAS_GENAI_SDK:
                logger.warning("google.generativeai SDK not available. Falling back to Vertex AI HTTP endpoint.")
                self.use_vertex_ai = True
                self.vertex_ai_base_url = "https://aiplatform.googleapis.com/v1"
                self.model = None
            else:
                logger.error(f"Unknown API key format. Expected 'AIza...' or 'AQ.Ab...'. Got: {self.api_key[:10]}...")
                raise ValueError("Invalid API key format. Expected Generative Language API key (AIza...) or Vertex AI key (AQ.Ab...)")
        
        # Initialize HTTP client for Vertex AI (if needed)
        if self.use_vertex_ai:
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.ai_model_timeout + 10, connect=10.0),
            )
        else:
            self.http_client = None
    
    def _ensure_model(self) -> None:
        """Ensure model/client is initialized, raise if not available."""
        if self.use_vertex_ai:
            if self.http_client is None:
                raise RuntimeError("Vertex AI HTTP client is not available. Please check API key configuration.")
        else:
            if self.model is None:
                raise RuntimeError("Gemini model is not available. Please check API key configuration.")

    def filter_option_chain(
        self, chain_data: dict[str, Any], spot_price: float
    ) -> dict[str, Any]:
        """
        Filter option chain to keep only strikes within ±15% of spot price.
        Crucial for saving Token costs and reducing AI hallucinations.

        Args:
            chain_data: Full option chain data
            spot_price: Current spot price

        Returns:
            Filtered option chain
        """
        # Handle edge case where spot_price might be 0 or missing
        if not spot_price or spot_price <= 0:
            logger.warning("Invalid spot price for filtering. Returning full chain (risky).")
            return chain_data

        filtered = {"calls": [], "puts": []}
        threshold_low = spot_price * 0.85
        threshold_high = spot_price * 1.15

        for option_type in ["calls", "puts"]:
            if option_type not in chain_data:
                continue

            for option in chain_data[option_type]:
                strike = option.get("strike", 0)
                if threshold_low <= strike <= threshold_high:
                    filtered[option_type].append(option)

        logger.info(
            f"Filtered option chain: {len(filtered['calls'])} calls, "
            f"{len(filtered['puts'])} puts (spot: ${spot_price:.2f})"
        )
        return filtered

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    @gemini_circuit_breaker
    async def generate_report(
        self, strategy_data: dict[str, Any], option_chain: dict[str, Any]
    ) -> str:
        """
        Generate AI analysis report using Gemini with circuit breaker and retry.

        Args:
            strategy_data: Strategy configuration
            option_chain: Filtered option chain data

        Returns:
            Markdown-formatted report

        Raises:
            CircuitBreakerError: If circuit breaker is open
            ValueError: If response is invalid
            RuntimeError: If model is not available
        """
        # Check if model is available
        self._ensure_model()
        # 1. Pre-processing: Filter data to prevent Context Window Overflow
        spot_price = option_chain.get("spot_price", 0)
        filtered_chain = self.filter_option_chain(option_chain, spot_price)

        # 2. Load prompt template from config service (with fallback to default)
        prompt_template = await config_service.get(
            "ai.report_prompt_template",
            default=DEFAULT_REPORT_PROMPT_TEMPLATE
        )

        # 3. Format prompt with actual data
        try:
            prompt = prompt_template.format(
                strategy_data=json.dumps(strategy_data, indent=2),
                filtered_chain=json.dumps(filtered_chain, indent=2)
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Error formatting prompt template: {e}. Using default template.")
            # Fallback to default template if custom template has format errors
            prompt = DEFAULT_REPORT_PROMPT_TEMPLATE.format(
                strategy_data=json.dumps(strategy_data, indent=2),
                filtered_chain=json.dumps(filtered_chain, indent=2)
            )

        try:
            logger.info("Sending report request to Gemini...")
            
            if self.use_vertex_ai:
                # Use Vertex AI HTTP endpoint
                report = await self._call_vertex_ai(prompt)
            else:
                # Use Generative Language API SDK
                response = await asyncio.wait_for(
                    self.model.generate_content_async(prompt),
                    timeout=settings.ai_model_timeout
                )
                
                # Validate response exists
                if not response or not hasattr(response, 'text'):
                    raise ValueError("Invalid response from Gemini API")
                
                report = response.text

            # Validate response is meaningful
            if not report or len(report) < 100:
                raise ValueError("AI response too short or empty")

            return report
        except CircuitBreakerError:
            logger.error("Gemini API circuit breaker is OPEN")
            raise
        except Exception as e:
            logger.error(f"Gemini API error during report generation: {e}", exc_info=True)
            raise
    
    async def _call_vertex_ai(self, prompt: str) -> str:
        """Call Vertex AI endpoint using HTTP."""
        url = f"{self.vertex_ai_base_url}/publishers/google/models/{self.model_name}:generateContent"
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ]
        }
        
        headers = {
            "Content-Type": "application/json",
        }
        
        try:
            response = await self.http_client.post(
                url,
                headers=headers,
                json=payload,
                params={"key": self.api_key}
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Extract text from Vertex AI response
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    texts = []
                    for part in candidate["content"]["parts"]:
                        if "text" in part:
                            texts.append(part["text"])
                    return "".join(texts)
            
            raise ValueError("Invalid response format from Vertex AI")
        except httpx.HTTPStatusError as e:
            error_msg = f"Vertex AI HTTP error: {e.response.status_code}"
            if e.response.text:
                try:
                    error_data = e.response.json()
                    error_msg += f" - {error_data.get('error', {}).get('message', e.response.text)}"
                except:
                    error_msg += f" - {e.response.text[:200]}"
            raise RuntimeError(error_msg) from e
        except httpx.RequestError as e:
            raise ConnectionError(f"Failed to connect to Vertex AI: {e}") from e

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    @gemini_circuit_breaker
    async def generate_daily_picks(self) -> list[dict[str, Any]]:
        """
        Generate daily AI strategy picks using Gemini with Google Search.
        Forces JSON output format.

        Returns:
            List of strategy recommendation cards

        Raises:
            CircuitBreakerError: If circuit breaker is open
            ValueError: If response is invalid or empty
            RuntimeError: If model is not available
        """
        # Check if model is available
        self._ensure_model()
        
        # Load prompt from config service (with fallback to default)
        prompt = await config_service.get(
            "ai.daily_picks_prompt",
            default=DEFAULT_DAILY_PICKS_PROMPT
        )
        # Configure model to output JSON specifically for this call
        # For Vertex AI, we rely on prompt instructions to ensure JSON output
        # For SDK, we can use GenerationConfig
        config = None if self.use_vertex_ai else (GenerationConfig(temperature=0.7) if HAS_GENAI_SDK else None)

        try:
            logger.info("Generating Daily Picks via Gemini...")
            
            if self.use_vertex_ai:
                # Use Vertex AI HTTP endpoint
                raw_text = await self._call_vertex_ai(prompt)
            else:
                # Use Generative Language API SDK
                if config:
                    response = await asyncio.wait_for(
                        self.model.generate_content_async(prompt, generation_config=config),
                        timeout=settings.ai_model_timeout
                    )
                else:
                    response = await asyncio.wait_for(
                        self.model.generate_content_async(prompt),
                        timeout=settings.ai_model_timeout
                    )
                
                # Validate response exists
                if not response or not hasattr(response, 'text'):
                    raise ValueError("Invalid response from Gemini API")
                
                raw_text = response.text
            
            # Cleaning: Remove markdown code fences if present (e.g. ```json ... ```)
            cleaned_text = re.sub(r"```json\s*|\s*```", "", raw_text).strip()
            
            picks = json.loads(cleaned_text)
            
            if not isinstance(picks, list):
                logger.warning("AI returned valid JSON but not a list. Wrapping it.")
                picks = [picks]
            
            # Validate picks are not empty
            if not picks or len(picks) == 0:
                raise ValueError("AI returned empty picks list")

            logger.info(f"Successfully generated {len(picks)} daily picks.")
            return picks

        except CircuitBreakerError:
            logger.error("Gemini API circuit breaker is OPEN for daily picks")
            raise
        except json.JSONDecodeError as e:
            raw_preview = raw_text[:100] if 'raw_text' in locals() else "N/A"
            logger.error(f"Failed to parse AI JSON response: {e}. Raw: {raw_preview}...", exc_info=True)
            raise ValueError(f"Invalid JSON response from AI: {e}")
        except Exception as e:
            logger.error(f"Failed to generate daily picks: {e}", exc_info=True)
            raise


# Global Gemini provider instance
# Initialize with error handling to allow app to start even if Gemini is unavailable
try:
    gemini_provider = GeminiProvider()
except Exception as e:
    logger.error(f"Failed to initialize Gemini provider: {e}", exc_info=True)
    # Create a dummy provider that will raise RuntimeError when methods are called
    # This allows the app to start, but AI features will be disabled
    class DummyGeminiProvider(GeminiProvider):
        def __init__(self):
            self.model = None
            logger.warning("Using dummy Gemini provider - AI features disabled")
        
        def _ensure_model(self) -> None:
            raise RuntimeError("Gemini provider is not available. Please check API key configuration.")
    
    gemini_provider = DummyGeminiProvider()