"""Gemini Image Generation Provider for Strategy Charts."""

import asyncio
import base64
import json
import logging
from typing import Any

import httpx
from pybreaker import CircuitBreaker, CircuitBreakerError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Try to import google-genai (new SDK for Vertex AI)
try:
    from google import genai
    import vertexai
    from google.genai import types
    HAS_GENAI_SDK = True
    HAS_VERTEX_AI = True
except ImportError:
    HAS_GENAI_SDK = False
    HAS_VERTEX_AI = False
    genai = None
    vertexai = None
    types = None

# Fallback to old google.generativeai if new SDK not available
if not HAS_GENAI_SDK:
    try:
        import google.generativeai as genai_old
        HAS_OLD_GENAI_SDK = True
        genai_old_sdk = genai_old
    except ImportError:
        HAS_OLD_GENAI_SDK = False
        genai_old_sdk = None
else:
    HAS_OLD_GENAI_SDK = False
    genai_old_sdk = None

from app.core.config import settings

logger = logging.getLogger(__name__)

# Circuit breaker for image generation API
image_circuit_breaker = CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
)


# Wall Street Strategist prompt template (Optimized by Gemini - v2)
WALL_STREET_PROMPT_TEMPLATE = """# Task & Role
Act as a world-class Financial Data Visualization Expert. Create a high-quality, professional, wide-format infographic illustrating an options trading strategy.

# Strict Visual Constraints (DO NOT DEVIATE)
1. **Art Style:** Modern Flat Vector Illustration. Clean, minimalist, corporate design (like Stripe or Airbnb design systems). No photorealism, no messy sketches, no textbook scan look.
2. **Aspect Ratio:** Wide Panoramic (16:9 landscape). The image must be wide.
3. **Background:** Pure, clean white background with a very subtle, minimalist light-grey grid pattern.
4. **Color Palette (Strict Rule):**
    * **Vibrant Green:** Use for all positive elements: BUY legs, Long positions, Profit zones, Max Profit labels.
    * **Clear Red:** Use for all negative elements: SELL legs, Short positions, Loss zones, Max Loss labels.
    * **Neutral Grey:** Use for axes, timelines, net cash flow arrows, and neutral labels.

# Composition Layout (Horizontally Split Screen)
Divide the image horizontally into two distinct sections with clear titles.

## Section 1 (Top, ~30% height): "Opening Strategy Structure"
* **Title:** "Opening Strategy Structure: {strategy_name} ({ticker})"
* **Timeline:** Draw a clean, horizontal price timeline axis labeled "Strike Price ($)".
* **Legs Visualization:** Use large, stylized vector arrows aligned to their strike prices on the axis.
    * For BUY legs: Use a thick **Green Up Arrow**. Label it clearly (e.g., "BUY [Strike] [Type] (Long [Type])").
    * For SELL legs: Use a thick **Red Down Arrow**. Label it clearly (e.g., "SELL [Strike] [Type] (Short [Type])").
* **Legs Structure Details:**
{legs_text}
* **Net Cash Flow:** Below the arrows, draw a prominent horizontal grey arrow spanning the width, pointing right. Label it "Net Cash Flow: {net_cash_flow}".
* **Ticker Info:** In the top right corner, add a small, clean box with "Ticker: {ticker} | Current Price: {current_price}".

## Section 2 (Bottom, ~70% height): "Payoff Diagram at Expiration"
* **Title:** "Payoff Diagram at Expiration ({ticker} {strategy_name})"
* **Chart Axes:** Draw a large, clear 2D chart. X-axis = "Stock Price at Expiration ($)". Y-axis = "Profit/Loss ($)".
* **Payoff Curve:** Draw a bold, continuous **Payoff Curve** that accurately represents the strategy's P/L at expiration. The shape must match the strategy type based on the legs structure (Long Straddle = V-shape, Long Call = upward slope, etc.).
* **Crucial Fill Rule (Area Tinting):**
    * Fill the entire area **BETWEEN** the curve and the X-axis with translucent **Green** where the curve is ABOVE the axis. Label this area "Profit Zone".
    * Fill the entire area **BETWEEN** the curve and the X-axis with translucent **Red** where the curve is BELOW the axis. Label this area "Loss Zone".
* **Annotations & Labels (Use clean vector elements):**
    * **Breakeven Point(s):** Mark all breakeven points on the X-axis with distinct dots and clear labels. Use EXACT values provided - DO NOT calculate. If multiple breakevens are provided (e.g., "{breakeven}"), mark ALL points with clear dots/labels (e.g., "Breakeven Point: {breakeven}").
    * **Current Price:** Mark the {current_price} on the X-axis with a vertical dashed line extending to the curve, with a label and arrow (e.g., "Current Price: {current_price} (In [Profit/Loss] Zone)").
    * **Max Profit:** Identify the highest point(s) or plateau of the curve. Label it with a large arrow and text "Max Profit: {max_profit}".
    * **Max Loss:** Identify the lowest point(s) or plateau of the curve. Label it with a large arrow and text "Max Loss: {max_loss}".

# Financial Data (Use EXACT values - DO NOT calculate)
* **Net Credit/Debit:** {net_cash_flow}
* **Breakeven Point(s):** {breakeven}
* **Max Profit:** {max_profit}
* **Max Loss:** {max_loss}

# Negative Constraints (What to avoid)
* Do NOT generate messy, handwritten, or blurry text.
* Do NOT create photorealistic textures or 3D effects (keep it 2D flat).
* Do NOT clutter the chart with excessive tiny numbers on the axes; focus on the key labels.
* Do NOT add unnecessary decorative elements.
* Do NOT calculate breakevens or financial metrics yourself - use ONLY the provided values.

**Language:** English
"""


class GeminiImageProvider:
    """Gemini Image Generation Provider for Strategy Charts."""

    def __init__(self):
        """Initialize the image provider."""
        self.api_key = settings.google_api_key
        # Gemini only (ZenMux disabled) - direct Gemini API model name
        self.model_name = settings.ai_image_model

        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is required for image generation")

        # Initialize genai SDK for Gemini (ZenMux disabled)
        if HAS_GENAI_SDK:
            try:
                genai.configure(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to configure genai SDK: {e}")
        else:
            logger.warning("google.generativeai SDK not available. Will use HTTP API fallback.")

    def construct_image_prompt(self, strategy_summary: dict[str, Any] | None = None, strategy_data: dict[str, Any] | None = None, metrics: dict[str, Any] | None = None) -> str:
        """
        Construct the image generation prompt from strategy summary or legacy format.

        Args:
            strategy_summary: Complete strategy summary (preferred format)
            strategy_data: Legacy format - Strategy configuration (legs, symbol, etc.)
            metrics: Legacy format - Strategy metrics (net_cash_flow, max_profit, etc.)

        Returns:
            Formatted prompt string
        """
        # Use strategy_summary if available, otherwise use legacy format
        if strategy_summary:
            ticker = strategy_summary.get("symbol", "N/A")
            strategy_name = strategy_summary.get("strategy_name", "Custom Strategy")
            # Ensure current_price is a number (handle None case)
            spot_price_raw = strategy_summary.get("spot_price")
            current_price = float(spot_price_raw) if spot_price_raw is not None and isinstance(spot_price_raw, (int, float)) else 0.0
            
            legs = strategy_summary.get("legs", [])
            if not isinstance(legs, list):
                legs = []
            legs_text = ""
            for i, leg in enumerate(legs, 1):
                # Skip None or non-dict legs
                if not isinstance(leg, dict):
                    logger.warning(f"Skipping invalid leg in image prompt (not a dict): {leg}")
                    continue
                action = leg.get("action", "buy").upper()
                # Ensure strike is a number (handle None case)
                strike_raw = leg.get("strike")
                strike = float(strike_raw) if strike_raw is not None and isinstance(strike_raw, (int, float)) else 0.0
                option_type = leg.get("type", "call").upper()
                role = leg.get("role", "")
                if role:
                    role_text = f" (Role: {role})"
                else:
                    role_text = ""
                legs_text += f"    {i}. {action} {strike} {option_type}{role_text}\n"

            # Extract metrics from strategy_summary (handle None case)
            strategy_metrics = strategy_summary.get("strategy_metrics")
            if not isinstance(strategy_metrics, dict):
                strategy_metrics = {}
            trade_execution = strategy_summary.get("trade_execution")
            if not isinstance(trade_execution, dict):
                trade_execution = {}
            
            # Ensure net_cash_flow is a number (handle None case)
            net_cost_raw = trade_execution.get("net_cost")
            net_cash_flow = float(net_cost_raw) if net_cost_raw is not None and isinstance(net_cost_raw, (int, float)) else 0.0
            net_cash_flow_text = f"${net_cash_flow:+.2f}" if net_cash_flow != 0 else "$0.00"
            
            margin = 0  # Not in strategy_summary, set to 0
            margin_text = "N/A"
            
            breakeven_points = strategy_metrics.get("breakeven_points", [])
            # Format all breakeven points (Long Straddle/Strangle have 2, others may have 1)
            if breakeven_points and isinstance(breakeven_points, list) and len(breakeven_points) > 0:
                # Filter out None values and ensure all are numbers
                valid_breakevens = [
                    float(bp) for bp in breakeven_points 
                    if bp is not None and isinstance(bp, (int, float))
                ]
                if len(valid_breakevens) == 1:
                    breakeven_text = f"${valid_breakevens[0]:.2f}"
                elif len(valid_breakevens) > 1:
                    # Multiple breakeven points (e.g., Long Straddle)
                    breakeven_text = ", ".join([f"${bp:.2f}" for bp in valid_breakevens])
                else:
                    breakeven_text = "N/A"
            else:
                breakeven_text = "N/A"
            
            # Ensure max_profit is a number (handle None case)
            max_profit_raw = strategy_metrics.get("max_profit")
            max_profit = float(max_profit_raw) if max_profit_raw is not None and isinstance(max_profit_raw, (int, float)) else 0.0
            max_profit_text = f"${max_profit:,.2f}" if max_profit > 0 else "N/A"
            
            # Ensure max_loss is a number (handle None case)
            max_loss_raw = strategy_metrics.get("max_loss")
            max_loss = float(max_loss_raw) if max_loss_raw is not None and isinstance(max_loss_raw, (int, float)) else 0.0
            max_loss_text = f"${abs(max_loss):,.2f}" if max_loss < 0 else "N/A"
        elif strategy_data and metrics:
            # Legacy format (backward compatibility)
            ticker = strategy_data.get("symbol", "N/A")
            strategy_name = strategy_data.get("strategy_name", "Custom Strategy")
            # Ensure current_price is a number (handle None case)
            current_price_raw = strategy_data.get("current_price")
            current_price = float(current_price_raw) if current_price_raw is not None and isinstance(current_price_raw, (int, float)) else 0.0
            
            legs = strategy_data.get("legs", [])
            if not isinstance(legs, list):
                legs = []
            legs_text = ""
            for i, leg in enumerate(legs, 1):
                if not isinstance(leg, dict):
                    continue
                action = leg.get("action", "buy").upper()
                # Ensure strike is a number (handle None case)
                strike_raw = leg.get("strike")
                strike = float(strike_raw) if strike_raw is not None and isinstance(strike_raw, (int, float)) else 0.0
                option_type = leg.get("type", "call").upper()
                role = leg.get("role", "")
                if role:
                    role_text = f" (Role: {role})"
                else:
                    role_text = ""
                legs_text += f"    {i}. {action} {strike} {option_type}{role_text}\n"

            # Ensure net_cash_flow is a number (handle None case)
            net_cash_flow_raw = metrics.get("net_cash_flow")
            net_cash_flow = float(net_cash_flow_raw) if net_cash_flow_raw is not None and isinstance(net_cash_flow_raw, (int, float)) else 0.0
            net_cash_flow_text = f"${net_cash_flow:+.2f}" if net_cash_flow != 0 else "$0.00"
            
            # Ensure margin is a number (handle None case)
            margin_raw = metrics.get("margin")
            margin = float(margin_raw) if margin_raw is not None and isinstance(margin_raw, (int, float)) else 0.0
            margin_text = f"${margin:,.0f}" if margin > 0 else "N/A"
            
            # Legacy format may have single breakeven or list
            breakeven_raw = metrics.get("breakeven")
            if isinstance(breakeven_raw, list):
                # Filter out None values and ensure all are numbers
                valid_breakevens = [
                    float(bp) for bp in breakeven_raw 
                    if bp is not None and isinstance(bp, (int, float))
                ]
                if len(valid_breakevens) > 0:
                    breakeven_text = ", ".join([f"${bp:.2f}" for bp in valid_breakevens])
                else:
                    breakeven_text = "N/A"
            elif breakeven_raw is not None and isinstance(breakeven_raw, (int, float)):
                breakeven_text = f"${float(breakeven_raw):.2f}" if breakeven_raw > 0 else "N/A"
            else:
                breakeven_text = "N/A"
            
            # Ensure max_profit is a number (handle None case)
            max_profit_raw = metrics.get("max_profit")
            max_profit = float(max_profit_raw) if max_profit_raw is not None and isinstance(max_profit_raw, (int, float)) else 0.0
            max_profit_text = f"${max_profit:,.2f}" if max_profit > 0 else "N/A"
            
            # Ensure max_loss is a number (handle None case)
            max_loss_raw = metrics.get("max_loss")
            max_loss = float(max_loss_raw) if max_loss_raw is not None and isinstance(max_loss_raw, (int, float)) else 0.0
            max_loss_text = f"${abs(max_loss):,.2f}" if max_loss < 0 else "N/A"
        else:
            raise ValueError("Either strategy_summary or (strategy_data + metrics) must be provided")

        return WALL_STREET_PROMPT_TEMPLATE.format(
            ticker=ticker,
            strategy_name=strategy_name,
            current_price=f"${current_price:.2f}",
            legs_text=legs_text.strip(),
            net_cash_flow=net_cash_flow_text,
            margin=margin_text,
            breakeven=breakeven_text,
            max_profit=max_profit_text,
            max_loss=max_loss_text,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    @image_circuit_breaker
    async def generate_chart(
        self,
        prompt: str | None = None,
        strategy_summary: dict[str, Any] | None = None,
        strategy_data: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> str:
        """
        Generate an image chart.
        Auto-constructs prompt if strategy data is provided, otherwise uses the raw prompt string.

        Args:
            prompt: Optional raw prompt string (legacy support)
            strategy_summary: Complete strategy summary (preferred)
            strategy_data: Legacy strategy config
            metrics: Legacy metrics

        Returns:
            Base64-encoded image string

        Raises:
            ValueError: If image generation fails or no valid input provided
            httpx.HTTPError: If API request fails
        """
        # 1. 核心逻辑：如果没提供 raw prompt，但提供了策略数据，则在内部构建
        final_prompt = prompt

        if not final_prompt:
            if strategy_summary or (strategy_data and metrics):
                logger.info("Constructing image prompt internally from strategy data")
                final_prompt = self.construct_image_prompt(
                    strategy_summary=strategy_summary,
                    strategy_data=strategy_data,
                    metrics=metrics,
                )
            else:
                raise ValueError(
                    "Must provide either 'prompt' string OR strategy data (strategy_summary or strategy_data + metrics)"
                )

        # Log usage
        logger.debug(f"Generating image with prompt (first 100 chars): {final_prompt[:100]}...")

        # SDK required only for Generative Language API (AIza). Vertex AI (AQ.) uses HTTP.
        if not self.api_key.startswith("AQ.") and not HAS_GENAI_SDK:
            raise ValueError(
                "google-genai SDK is missing for Generative Language API. "
                "Use Vertex AI key (AQ.) or install: pip install google-genai"
            )

        # 强制检查：确保使用 Gemini 模型名，而不是 Imagen
        if self.model_name.startswith("imagen"):
            logger.warning(
                f"Model name '{self.model_name}' is configured, but complex charts require 'gemini-3-pro-image'. "
                f"Forcing use of Gemini model instead of Imagen API."
            )
            # 强制使用 Gemini 模型（在 _generate_with_genai_sdk 中会使用 gemini-3-pro-image）
        
        # 确保有 API key
        if not self.api_key:
            raise ValueError("Google API key is required for Gemini image generation")

        try:
            logger.info(f"Attempting to generate image using Gemini API flow (will use gemini-3-pro-image model)")
            # 坚定地只调用这一个方法，不降级到 Imagen API
            return await self._generate_with_gemini(final_prompt)

        except Exception as e:
            logger.error(f"Gemini image generation critical failure: {e}")
            # 移除降级到 _generate_with_imagen_api 的代码
            # 对于金融图表，宁愿失败也不要生成错误的图
            raise ValueError(
                f"Gemini image generation failed. Complex financial charts require Gemini models, "
                f"not Imagen API. Error: {str(e)}"
            ) from e

    # ZenMux disabled - image generation uses Gemini only
    # async def _generate_with_zenmux(self, prompt: str) -> str: ...

    async def _generate_with_gemini(self, prompt: str) -> str:
        """Generate image using Gemini (Vertex AI HTTP API or Generative Language API SDK).
        
        According to Google Cloud documentation:
        https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/image-generation
        
        - Use gemini-3-pro-image or gemini-2.5-flash-image model
        - Set responseModalities: ["TEXT", "IMAGE"] in generationConfig
        - Image data is in response.candidates[0].content.parts[0].inline_data.data
        
        Supports both:
        - Vertex AI API key (AQ.Ab...) -> Use HTTP API
        - Generative Language API key (AIza...) -> Use SDK
        """
        if not self.api_key:
            raise ValueError("Google API key is required for Gemini image generation")
        
        # Detect API key type
        is_vertex_ai_key = self.api_key.startswith("AQ.")
        is_genai_key = self.api_key.startswith("AIza")
        
        try:
            if is_vertex_ai_key:
                # Vertex AI API key - use HTTP REST API (same as text generation)
                return await self._generate_with_vertex_ai_http(prompt)
            elif is_genai_key and HAS_GENAI_SDK:
                # Generative Language API key - use SDK
                return await self._generate_with_genai_sdk(prompt)
            else:
                raise ValueError(
                    f"Unsupported API key format. "
                    f"For image generation, you need a Generative Language API key (AIza...). "
                    f"Got: {self.api_key[:10]}... "
                    f"Please obtain an API key from https://aistudio.google.com/app/apikey"
                )
        except Exception as e:
            logger.error(f"Gemini image generation failed: {e}")
            raise ValueError(f"Gemini image generation failed: {str(e)}") from e
    
    async def _generate_with_vertex_ai_http(self, prompt: str) -> str:
        """Generate image using Vertex AI REST API with API key (AQ.).
        
        Uses the same HTTP approach as text generation - POST to generateContent
        with ?key= parameter. Works with Vertex AI API key (AQ.) without ADC.
        
        Ref: https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/image-generation
        """
        project = getattr(settings, "google_cloud_project", None) or "friendly-vigil-481107-h3"
        locations = [
            getattr(settings, "google_cloud_location", None) or "global",
            "us-central1",  # Image models often available here
        ]
        locations = list(dict.fromkeys(locations))  # Dedupe

        model_ids_to_try = ["gemini-3-pro-image-preview", "gemini-2.5-flash-image"]
        if self.model_name and "2.5" in self.model_name:
            model_ids_to_try.insert(0, "gemini-2.5-flash-image")

        timeout = httpx.Timeout(120.0)
        last_error: Exception | None = None

        for location in locations:
            base_url = f"https://aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models"
            for model_id in model_ids_to_try:
                url = f"{base_url}/{model_id}:generateContent"
                payload = {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "responseModalities": ["TEXT", "IMAGE"],
                        "imageConfig": {"aspectRatio": "16:9"},
                    },
                }
                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        response = await client.post(
                            url,
                            json=payload,
                            params={"key": self.api_key},
                            headers={"Content-Type": "application/json"},
                        )
                        response.raise_for_status()
                        result = response.json()
                except httpx.HTTPStatusError as e:
                    last_error = e
                    if e.response.status_code == 404 or "not found" in (e.response.text or "").lower():
                        logger.warning(f"Model {model_id} in {location} not available, trying next...")
                        continue
                    err_obj = {}
                    try:
                        err_obj = e.response.json().get("error", {})
                    except Exception:
                        pass
                    raise ValueError(
                        f"Vertex AI image generation failed: {err_obj.get('message', e.response.text)}"
                    ) from e
                except Exception as e:
                    last_error = e
                    raise

                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    content = candidate.get("content", {})
                    parts = content.get("parts", [])
                    for part in parts:
                        inline = part.get("inlineData") or part.get("inline_data")
                        if inline and inline.get("data"):
                            image_b64 = inline["data"]
                            logger.info(f"Generated image via Vertex AI ({model_id}, {location})")
                            return image_b64
                        if part.get("text"):
                            logger.debug(f"Response text: {part.get('text', '')[:80]}...")

        raise ValueError(
            f"Vertex AI did not return image data. Last error: {last_error}. "
            "Try GOOGLE_CLOUD_LOCATION=us-central1 or use Generative Language API key (AIza...)."
        )
    
    async def _generate_with_genai_sdk(self, prompt: str) -> str:
        """Generate image using Generative Language API SDK."""
        if not HAS_GENAI_SDK:
            raise ValueError("Gemini SDK not available")
        
        # Configure genai with API key
        genai.configure(api_key=self.api_key)
        
        # Use Gemini 3 Pro Image model
        model_name = "gemini-3-pro-image"
        logger.info(f"Using Gemini SDK model {model_name} for image generation")
        
        model = genai.GenerativeModel(model_name)
        
        # Generate content - SDK may handle image generation automatically for image models
        response = await asyncio.to_thread(
            model.generate_content,
            prompt
        )
        
        # Extract image data from response
        # According to docs: response.candidates[0].content.parts[0].inline_data.data
        # Also check if response has a direct .image attribute (some SDK versions)
        if hasattr(response, 'image') and response.image:
            # Direct image attribute (some SDK versions)
            image_bytes = response.image
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            logger.info(f"Successfully generated image via Gemini SDK (direct .image attribute, {len(image_b64)} chars)")
            return image_b64
        
        # Standard path: extract from candidates[0].content.parts[0].inline_data.data
        if hasattr(response, 'candidates') and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                for part in candidate.content.parts:
                    # Check for inline image data
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_bytes = part.inline_data.data
                        # Convert to base64
                        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                        logger.info(f"Successfully generated image via Gemini SDK ({len(image_b64)} chars)")
                        return image_b64
                    # Also check for text that might contain image reference
                    if hasattr(part, 'text') and part.text:
                        logger.debug(f"Response contains text: {part.text[:100]}")
        
        raise ValueError("Gemini SDK response did not contain image data in expected format")


# Singleton instance
_image_provider: GeminiImageProvider | None = None


def get_image_provider() -> GeminiImageProvider:
    """Get or create the image provider singleton."""
    global _image_provider
    if _image_provider is None:
        _image_provider = GeminiImageProvider()
    return _image_provider
