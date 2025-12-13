"""ZenMux AI provider implementation using OpenAI-compatible API."""

import asyncio
import json
import logging
import re
from typing import Any

import httpx
from openai import AsyncOpenAI
from pybreaker import CircuitBreaker, CircuitBreakerError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.services.ai.base import BaseAIProvider
from app.services.config_service import config_service

logger = logging.getLogger(__name__)

# Default prompt templates (same as GeminiProvider for consistency)
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

# Circuit breaker for ZenMux API (independent from Gemini)
zenmux_circuit_breaker = CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
)


class ZenMuxProvider(BaseAIProvider):
    """ZenMux provider for AI analysis using OpenAI-compatible API."""

    def __init__(self) -> None:
        """Initialize ZenMux client using OpenAI SDK.
        
        ZenMux supports OpenAI-compatible API, so we can use the OpenAI SDK
        with a custom base_url and api_key.
        """
        # Ensure API key is configured
        if not settings.zenmux_api_key:
            logger.error("ZenMux API key is not configured. ZenMux features will not work.")
            raise ValueError("ZenMux API key is required for ZenMux provider")
        
        # Initialize OpenAI client with ZenMux endpoint
        try:
            self.client = AsyncOpenAI(
                api_key=settings.zenmux_api_key,
                base_url=settings.zenmux_api_base,
                timeout=httpx.Timeout(settings.ai_model_timeout + 10, connect=10.0),
            )
            self.model_name = settings.zenmux_model
            logger.info(f"ZenMux API configured with model: {self.model_name}")
            logger.info(f"ZenMux API base URL: {settings.zenmux_api_base}")
        except Exception as e:
            logger.error(f"Failed to initialize ZenMux client: {e}")
            raise ValueError(f"Failed to initialize ZenMux client: {e}")
    
    def _ensure_client(self) -> None:
        """Ensure client is initialized, raise if not available."""
        if not hasattr(self, 'client') or self.client is None:
            raise RuntimeError("ZenMux client is not available. Please check API key configuration.")

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
    @zenmux_circuit_breaker
    async def generate_report(
        self, strategy_data: dict[str, Any], option_chain: dict[str, Any]
    ) -> str:
        """
        Generate AI analysis report using ZenMux with circuit breaker and retry.

        Args:
            strategy_data: Strategy configuration
            option_chain: Filtered option chain data

        Returns:
            Markdown-formatted report

        Raises:
            CircuitBreakerError: If circuit breaker is open
            ValueError: If response is invalid
            RuntimeError: If client is not available
        """
        # Check if client is available
        self._ensure_client()
        
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
            logger.info(f"Sending report request to ZenMux (model: {self.model_name})...")
            
            # Use OpenAI ChatCompletion API (ZenMux compatible)
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.7,
                ),
                timeout=settings.ai_model_timeout
            )
            
            # Validate response exists
            if not response or not response.choices or len(response.choices) == 0:
                raise ValueError("Invalid response from ZenMux API")
            
            report = response.choices[0].message.content
            
            # Validate response is meaningful
            if not report or len(report) < 100:
                raise ValueError("AI response too short or empty")

            logger.info("Successfully received report from ZenMux")
            return report
            
        except CircuitBreakerError:
            logger.error("ZenMux API circuit breaker is OPEN")
            raise
        except asyncio.TimeoutError:
            logger.error(f"ZenMux API request timed out after {settings.ai_model_timeout}s")
            raise TimeoutError(f"Request timed out after {settings.ai_model_timeout} seconds")
        except Exception as e:
            logger.error(f"ZenMux API error during report generation: {e}", exc_info=True)
            raise

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    @zenmux_circuit_breaker
    async def generate_daily_picks(self) -> list[dict[str, Any]]:
        """
        Generate daily AI strategy picks using ZenMux.
        Forces JSON output format.

        Returns:
            List of strategy recommendation cards

        Raises:
            CircuitBreakerError: If circuit breaker is open
            ValueError: If response is invalid or empty
            RuntimeError: If client is not available
        """
        # Check if client is available
        self._ensure_client()
        
        # Load prompt from config service (with fallback to default)
        prompt = await config_service.get(
            "ai.daily_picks_prompt",
            default=DEFAULT_DAILY_PICKS_PROMPT
        )

        try:
            logger.info(f"Generating Daily Picks via ZenMux (model: {self.model_name})...")
            
            # Use OpenAI ChatCompletion API
            # Note: We rely on prompt instructions for JSON format (same as GeminiProvider)
            # Some models may not support response_format parameter
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.7,
                ),
                timeout=settings.ai_model_timeout
            )
            
            # Validate response exists
            if not response or not response.choices or len(response.choices) == 0:
                raise ValueError("Invalid response from ZenMux API")
            
            raw_text = response.choices[0].message.content
            
            if not raw_text:
                raise ValueError("Empty response from ZenMux API")
            
            # Cleaning: Remove markdown code fences if present (e.g. ```json ... ```)
            cleaned_text = re.sub(r"```json\s*|\s*```", "", raw_text).strip()
            
            # Parse JSON
            try:
                picks_data = json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}. Raw: {cleaned_text[:200]}...")
                raise ValueError(f"Invalid JSON response from AI: {e}")
            
            # Handle different JSON structures
            if isinstance(picks_data, dict):
                # If JSON is an object, try to extract a list from common keys
                if "picks" in picks_data:
                    picks = picks_data["picks"]
                elif "strategies" in picks_data:
                    picks = picks_data["strategies"]
                elif "recommendations" in picks_data:
                    picks = picks_data["recommendations"]
                else:
                    # If it's a single object, wrap it in a list
                    logger.warning("AI returned a single object, wrapping it in a list.")
                    picks = [picks_data]
            elif isinstance(picks_data, list):
                picks = picks_data
            else:
                raise ValueError(f"Unexpected JSON structure: {type(picks_data)}")
            
            # Validate picks are not empty
            if not picks or len(picks) == 0:
                raise ValueError("AI returned empty picks list")

            logger.info(f"Successfully generated {len(picks)} daily picks.")
            return picks

        except CircuitBreakerError:
            logger.error("ZenMux API circuit breaker is OPEN for daily picks")
            raise
        except asyncio.TimeoutError:
            logger.error(f"ZenMux API request timed out after {settings.ai_model_timeout}s")
            raise TimeoutError(f"Request timed out after {settings.ai_model_timeout} seconds")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI JSON response: {e}", exc_info=True)
            raise ValueError(f"Invalid JSON response from AI: {e}")
        except Exception as e:
            logger.error(f"Failed to generate daily picks: {e}", exc_info=True)
            raise


# Global ZenMux provider instance (lazy initialization via registry)
# This is kept for backward compatibility, but ProviderRegistry should be used
try:
    zenmux_provider = ZenMuxProvider()
except Exception as e:
    logger.error(f"Failed to initialize ZenMux provider: {e}", exc_info=True)
    # Create a dummy provider that will raise RuntimeError when methods are called
    class DummyZenMuxProvider(ZenMuxProvider):
        def __init__(self):
            self.client = None
            logger.warning("Using dummy ZenMux provider - AI features disabled")
        
        def _ensure_client(self) -> None:
            raise RuntimeError("ZenMux provider is not available. Please check API key configuration.")
    
    zenmux_provider = DummyZenMuxProvider()

