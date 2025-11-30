"""Google Gemini AI provider implementation."""

import json
import logging
import re
from typing import Any

import google.generativeai as genai
from google.generativeai.types import GenerationConfig
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
    timeout_duration=60,
    expected_exception=Exception,
)


class GeminiProvider(BaseAIProvider):
    """Gemini 3.0 Pro provider with Google Search grounding."""

    def __init__(self) -> None:
        """Initialize Gemini client.
        
        According to official Gemini SDK docs:
        - tools parameter should be a list or tool objects
        - For Google Search grounding, use tools parameter
        Docs: https://ai.google.dev/api/python/google/generativeai
        """
        # Ensure API key is configured
        genai.configure(api_key=settings.google_api_key)
        
        # Initialize model with Grounding enabled
        # According to docs, tools can be a list or tool objects
        # For Google Search grounding, pass as list or use genai.protos.Tool
        self.model = genai.GenerativeModel(
            model_name=settings.ai_model_default,  # e.g., "gemini-1.5-pro" or "gemini-2.0-flash"
            tools=["google_search"],  # List format for Google Search grounding
        )

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
        """
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
            response = await self.model.generate_content_async(prompt)
            
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
        """
        # Load prompt from config service (with fallback to default)
        prompt = await config_service.get(
            "ai.daily_picks_prompt",
            default=DEFAULT_DAILY_PICKS_PROMPT
        )
        # Configure model to output JSON specifically for this call
        # According to official Gemini SDK docs:
        # GenerationConfig supports response_mime_type parameter for structured output
        # Docs: https://ai.google.dev/api/python/google/generativeai
        config = GenerationConfig(response_mime_type="application/json")

        try:
            logger.info("Generating Daily Picks via Gemini...")
            response = await self.model.generate_content_async(prompt, generation_config=config)
            
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
            raw_preview = response.text[:100] if response and hasattr(response, 'text') else "N/A"
            logger.error(f"Failed to parse AI JSON response: {e}. Raw: {raw_preview}...", exc_info=True)
            raise ValueError(f"Invalid JSON response from AI: {e}")
        except Exception as e:
            logger.error(f"Failed to generate daily picks: {e}", exc_info=True)
            raise


# Global Gemini provider instance
gemini_provider = GeminiProvider()