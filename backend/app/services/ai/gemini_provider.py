"""Google Gemini AI provider implementation.

Supports both Generative Language API (AIza... keys) and Vertex AI (AQ.Ab... keys).
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any, Callable, Optional

import pytz

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

# Report date in US/Eastern for memo header (so output says "Date: February 7, 2026" = actual generation time)
def _report_date_utc_now() -> str:
    return datetime.now(pytz.timezone("US/Eastern")).strftime("%B %d, %Y")

# §6.5: Prompt templates from centralized config (app.core.prompts)
from app.core.prompts import PROMPTS, REPORT_TEMPLATE_V1, DAILY_PICKS_V1, get_prompt

DEFAULT_REPORT_PROMPT_TEMPLATE = PROMPTS.get(REPORT_TEMPLATE_V1) or get_prompt(REPORT_TEMPLATE_V1, "")
DEFAULT_DAILY_PICKS_PROMPT = PROMPTS.get(DAILY_PICKS_V1) or get_prompt(DAILY_PICKS_V1, "")

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
            # Vertex AI: preview/exp/2.5/2.0 models use us-central1 + v1beta1 for best tool support.
            self.use_vertex_ai = True
            self.vertex_ai_base_url = "https://aiplatform.googleapis.com/v1/publishers/google/models"
            project = settings.google_cloud_project or "friendly-vigil-481107-h3"
            # Preview/exp/gemini-2/gemini-3 -> us-central1 + v1beta1 (e.g. gemini-2.5-pro, gemini-3-flash-preview).
            is_preview = any(
                k in self.model_name for k in ["preview", "exp", "gemini-2", "gemini-3"]
            )
            if is_preview:
                location = "us-central1"
                api_version = "v1beta1"
                if "gemini-2.5" in self.model_name:
                    self.vertex_model_id = "gemini-2.5-pro"
                else:
                    self.vertex_model_id = self.model_name
            else:
                location = settings.google_cloud_location or "global"
                api_version = "v1"
                self.vertex_model_id = self.model_name
            self.vertex_ai_project_url = (
                f"https://aiplatform.googleapis.com/{api_version}/projects/{project}/locations/{location}/publishers/google/models"
            )
            self.model = None
            logger.info(
                "Vertex AI Init: Model=%s, Region=%s, API=%s",
                self.vertex_model_id, location, api_version,
            )
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
                self.vertex_ai_base_url = "https://aiplatform.googleapis.com/v1/publishers/google/models"
                project = settings.google_cloud_project or "friendly-vigil-481107-h3"
                is_preview = any(
                    k in self.model_name for k in ["preview", "exp", "gemini-2", "gemini-3"]
                )
                if is_preview:
                    if "gemini-2.5" in self.model_name:
                        self.vertex_model_id = "gemini-2.5-pro"
                    else:
                        self.vertex_model_id = self.model_name
                else:
                    self.vertex_model_id = self.model_name
                if is_preview:
                    location = "us-central1"
                    api_version = "v1beta1"
                else:
                    location = getattr(settings, "google_cloud_location", None) or "global"
                    api_version = "v1"
                self.vertex_ai_project_url = (
                    f"https://aiplatform.googleapis.com/{api_version}/projects/{project}/locations/{location}/publishers/google/models"
                )
                self.model = None
            else:
                logger.error(f"Unknown API key format. Expected 'AIza...' or 'AQ.Ab...'. Got: {self.api_key[:10]}...")
                raise ValueError("Invalid API key format. Expected Generative Language API key (AIza...) or Vertex AI key (AQ.Ab...)")
        
        # Initialize HTTP client for Vertex AI (if needed)
        # Deep Research / long reports need extra buffer; avoid ReadTimeout
        if self.use_vertex_ai:
            timeout_val = (settings.ai_model_timeout or 60) + 60
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(timeout_val, connect=10.0),
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
        self,
        strategy_summary: dict[str, Any] | None = None,
        strategy_data: dict[str, Any] | None = None,
        option_chain: dict[str, Any] | None = None,
        model_override: str | None = None,
    ) -> str:
        """
        Generate AI analysis report using Gemini with circuit breaker and retry.

        Args:
            strategy_summary: Complete strategy summary (preferred format) containing:
                - legs: Strategy legs with Greeks and pricing
                - portfolio_greeks: Combined portfolio-level Greeks
                - trade_execution: Trade execution details
                - strategy_metrics: Max profit, max loss, breakeven points
                - payoff_summary: Key payoff diagram points
            strategy_data: Legacy format - Strategy configuration
            option_chain: Legacy format - Filtered option chain data

        Returns:
            Markdown-formatted report

        Raises:
            CircuitBreakerError: If circuit breaker is open
            ValueError: If response is invalid
            RuntimeError: If model is not available
        """
        # Check if model is available
        self._ensure_model()
        
        # Check if this is an Agent request (from Agent Framework)
        if strategy_summary and strategy_summary.get("_agent_analysis_request"):
            # Agent mode: Extract prompt and system_prompt directly
            logger.debug("Agent mode: Processing agent analysis request")
            agent_prompt = strategy_summary.get("_agent_prompt", "")
            agent_system_prompt = strategy_summary.get("_agent_system_prompt", "")
            
            if not agent_prompt:
                raise ValueError("Agent request must include '_agent_prompt' field")
            
            # Call AI API with prompt and system prompt
            return await self._call_ai_api(
                agent_prompt,
                system_prompt=agent_system_prompt,
                model_override=model_override,
            )
        
        # Normal mode: Use strategy_summary or legacy format
        # 1. Use strategy_summary if available, otherwise convert legacy format
        if strategy_summary:
            # Use the complete strategy summary (preferred format)
            strategy_context = dict(strategy_summary)
            if option_chain:
                # Attach full option chain for deeper analysis
                strategy_context["option_chain"] = option_chain
        elif strategy_data and option_chain:
            # Legacy format: Convert to strategy_summary format
            logger.warning("Using legacy format (strategy_data + option_chain). Please migrate to strategy_summary format.")
            spot_price = option_chain.get("spot_price", 0)
            filtered_chain = self.filter_option_chain(option_chain, spot_price)
            # Create a simplified strategy_summary from legacy data
            strategy_context = {
                "strategy_info": strategy_data,
                "market_context": {
                    "spot_price": spot_price,
                    "filtered_option_chain": filtered_chain,
                },
            }
        else:
            raise ValueError("Either strategy_summary or (strategy_data + option_chain) must be provided")

        # 2. Format prompt (reusable method)
        prompt = await self._format_prompt(strategy_context)
        
        # 3. Call AI API and return report
        return await self._call_ai_api(prompt, model_override=model_override)
    
    async def _format_prompt(self, strategy_context: dict[str, Any] | None) -> str:
        """
        Format prompt from strategy context.
        
        Args:
            strategy_context: Strategy context dictionary (can be None)
            
        Returns:
            Formatted prompt string
        """
        # Handle None case
        if not isinstance(strategy_context, dict):
            logger.error("strategy_context is None or not a dict in _format_prompt")
            raise ValueError("strategy_context must be a dictionary")

        # Current report date (US/Eastern) so memo header uses actual generation time, not training-date hallucination
        report_date = _report_date_utc_now()

        # Extract data from strategy_summary for prompt formatting
        symbol = strategy_context.get("symbol", "N/A")
        strategy_name = strategy_context.get("strategy_name", "Custom Strategy")
        # Ensure spot_price is a number (handle None case)
        spot_price_raw = strategy_context.get("spot_price")
        spot_price = float(spot_price_raw) if spot_price_raw is not None and isinstance(spot_price_raw, (int, float)) else 0.0
        expiration_date = strategy_context.get("expiration_date") or strategy_context.get("expiry", "N/A")
        
        # Extract legs and format them (handle None case)
        legs = strategy_context.get("legs")
        if not isinstance(legs, list):
            legs = []
        legs_json = []
        for leg in legs:
            if not isinstance(leg, dict):
                logger.warning(f"Skipping invalid leg (not a dict): {leg}")
                continue
            legs_json.append({
                "action": leg.get("action", "buy").upper(),
                "quantity": leg.get("quantity", 1),
                "expiry": leg.get("expiry") or leg.get("expiration_date", "N/A"),
                "strike": leg.get("strike", 0),
                "type": leg.get("type", "call").upper(),
                "premium": leg.get("premium", 0),
                "delta": leg.get("delta"),
                "gamma": leg.get("gamma"),
                "theta": leg.get("theta"),
                "vega": leg.get("vega"),
                "implied_volatility": leg.get("implied_volatility") or leg.get("implied_vol"),
            })
        
        # Extract portfolio Greeks
        portfolio_greeks = strategy_context.get("portfolio_greeks") or {}
        if not isinstance(portfolio_greeks, dict):
            portfolio_greeks = {}
        net_delta = portfolio_greeks.get("delta", 0)
        net_gamma = portfolio_greeks.get("gamma", 0)
        net_theta = portfolio_greeks.get("theta", 0)
        net_vega = portfolio_greeks.get("vega", 0)
        
        # Extract strategy metrics (handle None case)
        strategy_metrics = strategy_context.get("strategy_metrics")
        if not isinstance(strategy_metrics, dict):
            strategy_metrics = {}
        # Safely extract and convert max_profit and max_loss to float
        max_profit_raw = strategy_metrics.get("max_profit")
        max_profit = float(max_profit_raw) if max_profit_raw is not None and isinstance(max_profit_raw, (int, float)) else 0.0
        max_loss_raw = strategy_metrics.get("max_loss")
        max_loss = float(max_loss_raw) if max_loss_raw is not None and isinstance(max_loss_raw, (int, float)) else 0.0
        breakeven_points = strategy_metrics.get("breakeven_points", [])
        if not isinstance(breakeven_points, list):
            breakeven_points = []
        # Filter out None values and ensure all are numbers
        breakeven_points = [float(be) for be in breakeven_points if be is not None and isinstance(be, (int, float))]
        breakevens = ", ".join([f"${be:.2f}" for be in breakeven_points]) if breakeven_points else "N/A"
        
        # Calculate average IV from legs (handle None legs)
        iv_values = []
        if isinstance(legs, list):
            for leg in legs:
                if isinstance(leg, dict):
                    iv = leg.get("implied_volatility") or leg.get("implied_vol", 0)
                    if iv:
                        iv_values.append(iv)
        current_iv = sum(iv_values) / len(iv_values) if iv_values else 0
        iv_info = f"{current_iv:.1f}% Absolute" if current_iv > 0 else "N/A (not available)"
        
        # Estimate Probability of Profit (simplified - can be improved with Black-Scholes)
        # For now, use a heuristic based on max profit and max loss
        risk_reward = abs(max_profit / max_loss) if max_loss < 0 else 0
        pop_estimate = min(95, max(5, 50 + (risk_reward - 1) * 15))  # Rough estimate: 50% base, adjust by risk/reward
        
        # 3. Load prompt template from config service (with fallback to default)
        prompt_template = await config_service.get(
            "ai.report_prompt_template",
            default=DEFAULT_REPORT_PROMPT_TEMPLATE
        )

        # Extract trade execution and payoff summary for complete data
        trade_execution = strategy_context.get("trade_execution")
        if not isinstance(trade_execution, dict):
            trade_execution = {}
        
        payoff_summary = strategy_context.get("payoff_summary")
        if not isinstance(payoff_summary, dict):
            payoff_summary = {}
        
        # 4. Format prompt with extracted data
        try:
            formatted_prompt = prompt_template.format(
                symbol=symbol,
                strategy_name=strategy_name,
                spot_price=f"{spot_price:.2f}",
                iv_info=iv_info,
                legs_json=json.dumps(legs_json, indent=2),
                max_profit=f"{max_profit:,.2f}",
                max_loss=f"{max_loss:,.2f}",
                pop=f"{pop_estimate:.0f}",
                breakevens=breakevens,
                net_delta=f"{net_delta:.4f}",
                net_gamma=f"{net_gamma:.4f}",
                net_theta=f"{net_theta:.4f}",
                net_vega=f"{net_vega:.4f}",
                report_date=report_date,
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Error formatting prompt template: {e}. Using default template with JSON fallback.")
            # Fallback: use JSON format if template formatting fails
            formatted_prompt = f"""You are a Senior Derivatives Strategist at a top-tier Hedge Fund.

Analyze this options strategy and produce a comprehensive Investment Memo in Markdown format.

**Report Date (MANDATORY - use this exact date in the memo header; do NOT use any other date):** {report_date}

At the very top of the memo, include this header block using the Report Date above:
To: Investment Committee
From: Senior Derivatives Strategist
Date: {report_date}
Subject: Investment Memo: [ticker] [strategy name]

**Strategy Data:**
{json.dumps(strategy_context, indent=2)}

**Analysis Requirements:**
1. Market Context & Grounding (Use Google Search for latest news)
2. Risk/Reward Stress Test (Greeks analysis, tail risk)
3. Verdict & Score (0-10 risk/reward score)

**Output Format:**
- 📊 Executive Summary
- 🔍 Market Alignment (Fundamental & IV)
- 🛠️ Strategy Mechanics & Greeks
- ⚠️ Scenario Analysis (Bull Case, Bear Case, Stagnant)
- 💡 Final Verdict: [Score]/10

Write the investment memo:"""
        
        # IMPORTANT: Append complete strategy_summary JSON to the prompt (§6.4: include FMP/Tiger data when present)
        # This ensures all data (trade_execution, payoff_summary, fundamental_profile, iv_context, etc.) is available to the AI
        complete_strategy_data = {
            "symbol": symbol,
            "strategy_name": strategy_name,
            "spot_price": spot_price,
            "expiration_date": expiration_date,
            "legs": legs_json,
            "portfolio_greeks": {
                "delta": net_delta,
                "gamma": net_gamma,
                "theta": net_theta,
                "vega": net_vega,
            },
            "strategy_metrics": {
                "max_profit": max_profit,
                "max_loss": max_loss,
                "breakeven_points": breakeven_points,
            },
            "trade_execution": trade_execution,
            "payoff_summary": payoff_summary,
        }
        if strategy_context.get("fundamental_profile"):
            complete_strategy_data["fundamental_profile"] = strategy_context["fundamental_profile"]
        if strategy_context.get("iv_context"):
            complete_strategy_data["iv_context"] = strategy_context["iv_context"]
        if strategy_context.get("analyst_data"):
            complete_strategy_data["analyst_data"] = strategy_context["analyst_data"]
        
        # Append complete data as JSON for reference
        complete_data_section = f"""

---

**Complete Strategy Summary (JSON format for reference):**
```json
{json.dumps(complete_strategy_data, indent=2, default=str)}
```

**Additional Context:**
- Trade Execution Details: {json.dumps(trade_execution, indent=2) if trade_execution else "N/A"}
- Payoff Summary: {json.dumps(payoff_summary, indent=2) if payoff_summary else "N/A"}
"""
        
        return formatted_prompt + complete_data_section
    
    async def _call_ai_api(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model_override: str | None = None,
    ) -> str:
        """
        Call AI API with formatted prompt and optional system prompt.
        
        Args:
            prompt: Formatted prompt string
            system_prompt: Optional system prompt (for Agent Framework)
            model_override: Optional model id for this request (e.g. gemini-2.5-pro)
            
        Returns:
            Generated report
        """
        try:
            logger.info("Sending report request to Gemini...")
            
            if self.use_vertex_ai:
                # Use Vertex AI HTTP endpoint
                report = await self._call_vertex_ai(
                    prompt,
                    system_prompt=system_prompt,
                    model_override=model_override,
                )
            else:
                # Use Generative Language API SDK
                if system_prompt:
                    # SDK supports system instruction via system_instruction parameter
                    if HAS_GENAI_SDK:
                        from google.generativeai.types import HarmCategory, HarmBlockThreshold
                        # Create system instruction
                        response = await asyncio.wait_for(
                            self.model.generate_content_async(
                                prompt,
                                system_instruction=system_prompt
                            ),
                            timeout=settings.ai_model_timeout
                        )
                    else:
                        # Fallback: Prepend system prompt to user prompt
                        logger.warning("SDK not available, prepending system prompt to user prompt")
                        full_prompt = f"{system_prompt}\n\n{prompt}"
                        response = await asyncio.wait_for(
                            self.model.generate_content_async(full_prompt),
                            timeout=settings.ai_model_timeout
                        )
                else:
                    # No system prompt, use regular call
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
    
    async def _generate_prompt_preview(self, strategy_summary: dict[str, Any]) -> str:
        """
        Generate prompt preview for logging/debugging.
        
        Args:
            strategy_summary: Strategy summary dictionary
            
        Returns:
            Prompt preview string
        """
        try:
            return await self._format_prompt(strategy_summary)
        except Exception as e:
            logger.warning(f"Failed to generate prompt preview: {e}")
            return f"Error generating prompt preview: {str(e)}\n\nStrategy Summary:\n{json.dumps(strategy_summary, indent=2)}"
    
    def _vertex_supports_system_instruction(self) -> bool:
        """True if model supports systemInstruction in request body (e.g. gemini-2.5-pro, gemini-3-flash-preview)."""
        model_id = getattr(self, "vertex_model_id", None) or self.model_name
        return (
            model_id.startswith("gemini-2.0-flash")
            or model_id.startswith("gemini-2.5")
            or model_id.startswith("gemini-3")
        )

    def _vertex_thinking_config(
        self, model_id: str, thinking_level: str = "HIGH"
    ) -> dict[str, Any] | None:
        """GenerationConfig.thinkingConfig for Vertex thinking models.

        Disabled for gemini-2.5-pro; only dedicated thinking models (e.g. gemini-2.0-flash-thinking-exp) support this field.
        """
        return None

    # Default safetySettings: BLOCK_ONLY_HIGH to reduce false positives for financial content
    _VERTEX_SAFETY_SETTINGS: list[dict[str, str]] = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
    ]

    async def _call_vertex_generate_content(
        self,
        prompt: str,
        system_prompt: str | None = None,
        use_search: bool = False,
        json_mode: bool = False,
        max_output_tokens: int = 8192,
        timeout_sec: int | None = None,
        model_override: str | None = None,
    ) -> str:
        """Unified Vertex AI generateContent (gemini-2.5-pro: full JSON/Search/systemInstruction)."""
        model_id = (model_override or getattr(self, "vertex_model_id", None) or self.model_name).strip()
        url = f"{self.vertex_ai_project_url}/{model_id}:generateContent"
        request_timeout = timeout_sec if timeout_sec is not None else (settings.ai_model_timeout or 60) + 60

        # 1. System Prompt: 2.5/2.0 原生支持 systemInstruction；仅在不支持时拼接到 user prompt
        effective_prompt = prompt
        if system_prompt and not self._vertex_supports_system_instruction():
            effective_prompt = f"System Instruction:\n{system_prompt}\n\nUser Query:\n{prompt}"
            system_prompt = None
            logger.debug("Vertex AI: prepended systemInstruction to prompt (model %s)", model_id)

        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": effective_prompt}]}]
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        # 2. Generation Config
        gen_config: dict[str, Any] = {
            "temperature": 1.0 if use_search else 0.7,
            "maxOutputTokens": max_output_tokens,
        }
        if json_mode:
            gen_config["responseMimeType"] = "application/json"
        payload["generationConfig"] = gen_config
        payload["safetySettings"] = self._VERTEX_SAFETY_SETTINGS

        # 3. Tools: 2.0/2.5/3.x 用 googleSearch；1.5 用 googleSearchRetrieval (REST 驼峰)
        if use_search:
            model_id_str = str(getattr(self, "vertex_model_id", "") or model_id)
            use_new_tool = "gemini-2" in model_id_str or "gemini-3" in model_id_str
            if use_new_tool:
                payload["tools"] = [{"googleSearch": {}}]
            else:
                payload["tools"] = [{
                    "googleSearchRetrieval": {
                        "dynamicRetrievalConfig": {
                            "mode": "MODE_DYNAMIC",
                            "dynamicThreshold": 0.3,
                        }
                    }
                }]

        headers = {"Content-Type": "application/json"}

        # Retry on 429 (Resource Exhausted) with longer backoff (quota often resets per-minute)
        max_429_retries = 5
        wait_secs = (20, 45, 90, 120, 180)  # 5 retries: ~7.5 min total wait before giving up
        last_429_msg = ""

        try:
            for attempt in range(max_429_retries + 1):
                response = await self.http_client.post(
                    url,
                    headers=headers,
                    json=payload,
                    params={"key": self.api_key},
                    timeout=httpx.Timeout(request_timeout, connect=10.0),
                )

                if response.status_code == 429:
                    try:
                        err_json = response.json()
                        last_429_msg = err_json.get("error", {}).get("message", response.text)
                    except Exception:
                        last_429_msg = response.text[:200]
                    if attempt < max_429_retries:
                        wait_sec = wait_secs[attempt] if attempt < len(wait_secs) else 180
                        logger.warning(
                            "Vertex AI 429 (quota exhausted), retry %s/%s in %ss: %s",
                            attempt + 1,
                            max_429_retries,
                            wait_sec,
                            last_429_msg[:100],
                        )
                        await asyncio.sleep(wait_sec)
                        continue
                    logger.error(
                        "Vertex AI Failed [429] after %s retries: %s",
                        max_429_retries,
                        last_429_msg[:500],
                    )
                    raise RuntimeError(f"Vertex AI Error 429: {last_429_msg}")

                if response.status_code >= 400:
                    error_text = response.text
                    logger.error(
                        "Vertex AI Failed [%s]: %s\nPayload keys: %s",
                        response.status_code,
                        error_text[:500],
                        list(payload.keys()),
                    )
                    try:
                        err_json = response.json()
                        err_msg = f"{err_json.get('error', {}).get('message', error_text)}"
                    except Exception:
                        err_msg = error_text
                    raise RuntimeError(f"Vertex AI Error {response.status_code}: {err_msg}")

                response.raise_for_status()
                result = response.json()
                break

            # 4. Response Handling
            if "candidates" not in result or len(result["candidates"]) == 0:
                # 检查是否被 PromptFeedback 拦截
                feedback = result.get("promptFeedback", {})
                if feedback:
                    logger.warning("Request blocked. Feedback: %s", feedback)
                    return "Error: Request blocked by AI safety filters."

                # 某些情况下，candidates 为空但没有报错，视为生成失败
                logger.warning("Empty candidates. Full response: %s", json.dumps(result)[:200])
                return ""

            candidate = result["candidates"][0]
            finish_reason = candidate.get("finishReason")

            # 5. Safety Handling
            if finish_reason == "SAFETY":
                logger.warning("Safety block: %s", candidate.get("safetyRatings"))
                return "Error: Content blocked by safety filters."

            # 6. Text Extraction
            if "content" in candidate and "parts" in candidate["content"]:
                texts = [p["text"] for p in candidate["content"]["parts"] if "text" in p]
                if texts:
                    return "".join(texts)

            logger.warning("No text content found in Vertex AI response: %s", candidate)
            return ""

        except httpx.ReadTimeout:
            logger.error("Vertex AI ReadTimeout. Consider increasing ai_model_timeout.")
            raise ConnectionError("Vertex AI Timeout - Report generation took too long.") from None
        except httpx.RequestError as e:
            raise ConnectionError(f"Failed to connect to Vertex AI: {e}") from e

    async def _call_vertex_ai(
        self, prompt: str, system_prompt: str | None = None, model_override: str | None = None
    ) -> str:
        """
        Call Vertex AI generateContent (no tools). Uses unified _call_vertex_generate_content.
        """
        return await self._call_vertex_generate_content(
            prompt,
            system_prompt=system_prompt,
            use_search=False,
            max_output_tokens=8192,
            model_override=model_override,
        )

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

    async def _call_gemini_with_search(
        self,
        prompt: str,
        use_search: bool = True,
        system_prompt: str | None = None,
        json_mode: bool = False,
        max_output_tokens: int = 8192,
        timeout_sec: int | None = None,
        model_override: str | None = None,
    ) -> str:
        """
        Call Gemini with optional Google Search (grounding).

        Vertex AI: uses unified _call_vertex_generate_content (generationConfig,
        safetySettings BLOCK_ONLY_HIGH, no thinkingConfig).
        """
        if self.use_vertex_ai:
            logger.debug("Vertex AI request: use_search=%s", use_search)
            return await self._call_vertex_generate_content(
                prompt,
                system_prompt=system_prompt,
                use_search=use_search,
                json_mode=json_mode,
                max_output_tokens=max_output_tokens,
                timeout_sec=timeout_sec,
                model_override=model_override,
            )
        else:
            # Generative Language API SDK
            if not self.model:
                raise RuntimeError("Gemini SDK model is not available")
            
            # For SDK, use tools parameter to enable Google Search
            if use_search and HAS_GENAI_SDK:
                try:
                    # Enable Google Search retrieval tool
                    tools_config = [
                        {
                            "google_search_retrieval": {
                                "dynamic_retrieval_config": {
                                    "mode": "MODE_DYNAMIC",
                                    "dynamic_threshold": 0.3
                                }
                            }
                        }
                    ]
                    
                    # Build generate_content arguments
                    generate_kwargs = {"tools": tools_config}
                    if system_prompt:
                        generate_kwargs["system_instruction"] = system_prompt
                    
                    response = await asyncio.wait_for(
                        self.model.generate_content_async(
                            prompt,
                            **generate_kwargs
                        ),
                        timeout=settings.ai_model_timeout
                    )
                except Exception as e:
                    logger.error(f"Failed to call Gemini with search: {e}", exc_info=True)
                    raise
            else:
                # No search, but may have system prompt
                generate_kwargs = {}
                if system_prompt:
                    generate_kwargs["system_instruction"] = system_prompt
                
                response = await asyncio.wait_for(
                    self.model.generate_content_async(
                        prompt,
                        **generate_kwargs
                    ),
                    timeout=settings.ai_model_timeout
                )
            
            # Extract text from response
            if not response or not hasattr(response, 'text'):
                raise ValueError("Invalid response from Gemini API")
            
            return response.text

    def _filter_option_chain_for_recommendation(
        self, chain_data: dict[str, Any], spot_price: float, pct: float = 0.25
    ) -> dict[str, Any]:
        """Filter option chain to ±pct of spot for strategy recommendation (design: ±25% to control tokens)."""
        if not chain_data or not spot_price or spot_price <= 0:
            return chain_data or {"calls": [], "puts": []}
        low = spot_price * (1 - pct)
        high = spot_price * (1 + pct)
        filtered: dict[str, Any] = {"calls": [], "puts": []}
        for opt_type in ["calls", "puts"]:
            for opt in (chain_data.get(opt_type) or []):
                if isinstance(opt, dict) and low <= (opt.get("strike") or 0) <= high:
                    filtered[opt_type].append(opt)
        return filtered

    def _trim_fundamental_profile_for_planning(self, fp: dict[str, Any]) -> dict[str, Any]:
        """Keep only a small summary for planning phase to reduce token usage and 429 risk."""
        out: dict[str, Any] = {"ticker": fp.get("ticker")}
        # Key ratios only (no full financial statements / technical series)
        ratios = fp.get("ratios") or {}
        if isinstance(ratios, dict):
            out["ratios_summary"] = {
                k: (v if not isinstance(v, dict) else dict(list(v.items())[:5]))
                for k, v in list(ratios.items())[:4]
            }
        profile = fp.get("profile") or {}
        if isinstance(profile, dict):
            out["profile_summary"] = {k: profile.get(k) for k in ("sector", "industry", "companyName") if k in profile}
        # Drop: financial_statements, technical_indicators, risk_metrics, performance_metrics, valuation, dupont_analysis, volatility (full)
        return out

    def _trim_agent_summaries_for_planning(self, agent_summaries: Any) -> Any:
        """Trim agent summaries to ~300 chars each for planning to reduce token usage."""
        if not agent_summaries:
            return agent_summaries
        max_chars_per_section = 350
        if isinstance(agent_summaries, list):
            trimmed = []
            for item in agent_summaries:
                if isinstance(item, dict):
                    section = item.get("section") or item.get("name") or "Section"
                    content = item.get("content") or item.get("summary") or str(item)
                    s = content if isinstance(content, str) else json.dumps(content, default=str)
                    trimmed.append({"section": section, "content": s[:max_chars_per_section] + ("..." if len(s) > max_chars_per_section else "")})
                elif isinstance(item, str):
                    trimmed.append(item[:max_chars_per_section] + ("..." if len(item) > max_chars_per_section else ""))
                else:
                    trimmed.append(item)
            return trimmed[:10]  # at most 10 sections
        if isinstance(agent_summaries, dict):
            return {k: (v[:max_chars_per_section] + "..." if isinstance(v, str) and len(v) > max_chars_per_section else v) for k, v in list(agent_summaries.items())[:10]}
        return agent_summaries

    async def _summarize_agent_outputs_for_planning(self, agent_summaries: Any, symbol: str) -> str:
        """One Gemini call: summarize multi-agent outputs into a short text for planning/synthesis. Reduces token usage and 429 risk."""
        raw = json.dumps(agent_summaries, indent=2, default=str)
        if len(raw) > 28_000:
            raw = raw[:28_000] + "\n...[truncated for summarizer input.]"
        prompt = f"""You are a summarizer. Below is internal expert analysis from several specialists (fundamentals, Greeks, IV, risk scenarios, synthesis) for {symbol}.

Produce a concise summary in English only, under 400 words. Focus on:
- Key findings and main risks
- Greeks and IV takeaways
- Scenario conclusions (bull/bear/stagnant)
- Any corrective advice (hold/trim/avoid)

Output ONLY the summary text. No preamble, no "Summary:" label, no section headers."""
        prompt_full = f"{prompt}\n\n---\nInternal Expert Analysis:\n{raw}"
        try:
            out = await self._call_vertex_generate_content(
                prompt_full,
                use_search=False,
                max_output_tokens=1024,
                timeout_sec=120,
            )
            if out and isinstance(out, str) and len(out.strip()) >= 50:
                return out.strip()
        except Exception as e:
            logger.warning(f"Agent summarization failed, will use trimmed input: {e}")
        return ""

    def _format_deep_research_fundamental_context(self, strategy_context: dict[str, Any]) -> str:
        """Format enriched FMP data for Deep Research synthesis prompt."""
        parts = []
        fp = strategy_context.get("fundamental_profile")
        if fp and isinstance(fp, dict):
            parts.append(f"Fundamental Profile: {json.dumps(fp, indent=2, default=str)[:4000]}")
        ad = strategy_context.get("analyst_data")
        if ad and isinstance(ad, dict):
            parts.append(f"Analyst Data (estimates, price targets): {json.dumps(ad, indent=2, default=str)[:2000]}")
        events = strategy_context.get("upcoming_events") or strategy_context.get("catalyst") or []
        if events and isinstance(events, list):
            parts.append(f"Upcoming Events/Catalysts: {json.dumps(events[:8], indent=2, default=str)}")
        iv_ctx = strategy_context.get("iv_context")
        if iv_ctx and isinstance(iv_ctx, dict):
            parts.append(f"IV Context: {json.dumps(iv_ctx, indent=2, default=str)}")
        sent = strategy_context.get("sentiment") or {}
        if sent and isinstance(sent, dict):
            parts.append(f"Sentiment: {json.dumps(sent, indent=2, default=str)[:1500]}")
        ms = strategy_context.get("market_sentiment")
        if ms:
            parts.append(f"Market Sentiment: {str(ms)[:500]}")
        hist = strategy_context.get("historical_prices")
        if hist and isinstance(hist, list) and len(hist) > 2:
            parts.append(f"Historical Prices: {len(hist)} data points (recent closes available)")
        return "\n\n".join(parts) if parts else "No fundamental data available (rely on internal expert analysis and research findings)"

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    @gemini_circuit_breaker
    async def generate_strategy_recommendations(
        self,
        option_chain: dict[str, Any],
        strategy_summary: dict[str, Any],
        fundamental_profile: dict[str, Any],
        agent_summaries: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Phase A+: Generate 1-2 recommended option strategies from current chain + fundamentals + agent analysis.
        Returns list of strategies per design §3.5 (strategy_name, rationale, legs, estimated_net_credit, etc.).
        """
        self._ensure_model()
        spot = float(strategy_summary.get("spot_price") or 0)
        symbol = (strategy_summary.get("symbol") or "unknown").upper()
        expiration_date = strategy_summary.get("expiration_date") or strategy_summary.get("expiry") or "N/A"
        filtered_chain = self._filter_option_chain_for_recommendation(option_chain, spot, 0.25)
        chain_json = json.dumps(filtered_chain, indent=2, default=str)[:12000]
        profile_json = json.dumps(fundamental_profile, indent=2, default=str)[:6000]
        summaries_json = json.dumps(agent_summaries, indent=2, default=str)[:4000]
        user_legs = strategy_summary.get("legs") or []
        user_legs_json = json.dumps(user_legs, indent=2, default=str)[:2000]
        prompt = f"""You are a Senior Options Strategist. Given the current option chain (filtered to ±25% of spot), fundamental profile, and internal expert analysis, suggest 1 or 2 concrete option strategies that are low-cost and high win-rate for this symbol and expiration.

**Symbol:** {symbol}
**Expiration:** {expiration_date}
**Spot Price:** ${spot:.2f}

**User's current strategy (for context only):**
{user_legs_json}

**Option chain (calls and puts, ±25% of spot):**
{chain_json}

**Fundamental profile (summary):**
{profile_json}

**Internal expert analysis summaries:**
{summaries_json}

**Requirements:**
- Suggest 1 or 2 strategies (e.g. Bull Put Spread, Iron Condor, Covered Call, etc.).
- Each strategy must use ONLY strikes and expiration from the option chain above.
- Return a single JSON object with key "recommended_strategies", value an array of 1-2 objects.
- Each object: "strategy_name", "rationale" (1-2 sentences), "legs" (array of {{ "type": "call"|"put", "action": "buy"|"sell", "strike": number, "quantity": number, "expiry": "{expiration_date}" }}), "estimated_net_credit" (number, optional), "max_profit" (number, optional), "max_loss" (number, optional), "breakeven" (number, optional).
- All strikes must exist in the option chain. Expiry must be "{expiration_date}".
- Return ONLY valid JSON, no markdown or extra text.

Example format:
{{"recommended_strategies": [{{"strategy_name": "Bull Put Spread", "rationale": "...", "legs": [{{"type": "put", "action": "sell", "strike": 220, "quantity": 1, "expiry": "{expiration_date}"}}, {{"type": "put", "action": "buy", "strike": 215, "quantity": 1, "expiry": "{expiration_date}"}}], "estimated_net_credit": 0.85, "max_profit": 85, "max_loss": 415, "breakeven": 219.15}}]}}

Return the JSON:"""
        try:
            response = await self._call_gemini_with_search(prompt, use_search=False)
            if not response or not isinstance(response, str):
                return []
            cleaned = re.sub(r"```json\s*|\s*```", "", response).strip()
            data = json.loads(cleaned)
            strategies = data.get("recommended_strategies")
            if isinstance(strategies, list) and strategies:
                return strategies[:2]
            return []
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Strategy recommendation parse failed: {e}. Returning empty list.")
            return []

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    @gemini_circuit_breaker
    async def generate_deep_research_report(
        self,
        strategy_summary: dict[str, Any] | None = None,
        strategy_data: dict[str, Any] | None = None,
        option_chain: dict[str, Any] | None = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        agent_summaries: Optional[dict[str, Any]] = None,
        recommended_strategies: Optional[list[dict[str, Any]]] = None,
        internal_preliminary_report: Optional[str] = None,
        model_override: Optional[str] = None,
    ) -> str:
        """
        Generate deep research report using multi-step agentic workflow.
        
        When agent_summaries and recommended_strategies are provided (full pipeline),
        output is a three-part report: Fundamentals, User Strategy Review, System-Recommended Strategies.
        
        Args:
            strategy_summary: Complete strategy summary (preferred format)
            strategy_data: Legacy format - Strategy configuration
            option_chain: Legacy format - Filtered option chain data
            progress_callback: Optional callback(progress_percent, message) for progress updates
            agent_summaries: Optional Phase A summaries (for three-part report)
            recommended_strategies: Optional Phase A+ recommended strategies (for three-part report)
            
        Returns:
            Markdown-formatted deep research report (three-part when agent_summaries + recommended_strategies provided)
        """
        self._ensure_model()
        use_three_part = bool(agent_summaries is not None and recommended_strategies is not None)
        
        # Use strategy_summary if available, otherwise convert legacy format
        if strategy_summary:
            if not isinstance(strategy_summary, dict):
                raise ValueError("strategy_summary must be a dictionary")
            strategy_context = dict(strategy_summary)
            if option_chain:
                # Attach full option chain for deeper analysis
                strategy_context["option_chain"] = option_chain
            symbol = strategy_summary.get("symbol") or "the underlying"
        elif strategy_data and option_chain:
            # Legacy format: Convert to strategy_summary format
            logger.warning("Using legacy format in deep research. Please migrate to strategy_summary format.")
            spot_price = option_chain.get("spot_price", 0)
            filtered_chain = self.filter_option_chain(option_chain, spot_price)
            strategy_context = {
                "strategy_info": strategy_data,
                "market_context": {
                    "spot_price": spot_price,
                    "filtered_option_chain": filtered_chain,
                },
            }
            symbol = strategy_data.get("symbol") or "the underlying"
        else:
            raise ValueError("Either strategy_summary or (strategy_data + option_chain) must be provided")
        
        # Ensure symbol is a string (not None)
        if not symbol or not isinstance(symbol, str):
            symbol = "the underlying"
        
        spot = float(
            strategy_context.get("spot_price")
            or (strategy_context.get("market_context") or {}).get("spot_price")
            or 0
        )
        raw_chain = strategy_context.get("option_chain")

        # Planning phase: minimal context to reduce token usage and 429 risk (only need "list 4 questions").
        planning_data: dict[str, Any] = {
            "symbol": symbol,
            "spot_price": spot,
            "strategy_name": strategy_context.get("strategy_name", "Custom Strategy"),
            "legs": strategy_context.get("legs") or [],
        }
        fp = strategy_context.get("fundamental_profile")
        if fp and isinstance(fp, dict):
            planning_data["fundamental_profile"] = self._trim_fundamental_profile_for_planning(fp)
        # agent_analysis_summary filled in try block: either one Gemini summarization (preferred) or trimmed fallback

        # Progress helper
        def update_progress(percent: int, message: str) -> None:
            if progress_callback:
                try:
                    progress_callback(percent, message)
                except Exception as e:
                    logger.warning(f"Progress callback error: {e}")
            logger.info(f"[Deep Research {percent}%] {message}")

        agent_summary_condensed: str = ""

        try:
            # ========== STEP 0 (when multi-agent): Build planning context ==========
            if use_three_part and (agent_summaries or internal_preliminary_report):
                update_progress(2, "Preparing internal expert analysis for planning...")
                # Prefer internal_preliminary_report (Phase A synthesis) for planning; trim to reduce tokens
                if internal_preliminary_report and len(internal_preliminary_report) > 100:
                    planning_data["agent_analysis_summary"] = internal_preliminary_report[:5000]
                    logger.info("Using internal preliminary report for planning (~%s chars)", min(5000, len(internal_preliminary_report)))
                elif agent_summaries:
                    agent_summary_condensed = await self._summarize_agent_outputs_for_planning(agent_summaries, symbol)
                    if agent_summary_condensed:
                        planning_data["agent_analysis_summary"] = agent_summary_condensed
                    else:
                        planning_data["agent_analysis_summary"] = self._trim_agent_summaries_for_planning(agent_summaries)
            # Optional: tiny option chain sample (±5% ATM) for structure only
            if raw_chain and isinstance(raw_chain, dict) and spot > 0:
                try:
                    sample = self._filter_option_chain_for_recommendation(raw_chain, spot, pct=0.05)
                    if sample and (sample.get("calls") or sample.get("puts")):
                        planning_data["nearby_option_chain_sample"] = sample
                except Exception as e:
                    logger.debug("Skip option chain sample for planning: %s", e)
            elif raw_chain is not None:
                n = len(raw_chain) if isinstance(raw_chain, (list, dict)) else 0
                planning_data["option_chain_summary"] = f"[{n} option rows; omitted for token limit. Used in synthesis only.]"

            planning_json = json.dumps(planning_data, indent=2, default=str)
            _max_planning_chars = 60_000  # ~15k tokens for planning only; reduces 429 risk
            if len(planning_json) > _max_planning_chars:
                planning_json = planning_json[:_max_planning_chars] + "\n...[Strategy context truncated for length.]"

            # ========== STEP 1: PLANNING PHASE ==========
            update_progress(5, "Planning research questions...")

            planning_prompt = f"""You are a Lead Analyst. Given this option strategy (and internal expert analysis if provided), list 4 critical questions we must research via Google Search to evaluate risk/reward and supplement internal analysis.

Strategy Data:
{planning_json}

Requirements:
- List exactly 4 research questions that MUST be answered by Google Search (dates, numbers, ratings, news). Write all questions in English only.
- Each question should be specific and searchable (e.g. "{symbol} 2025 Q1 earnings date", "Wall Street price target {symbol}").
- If internal analysis is provided, base questions on it to complement (not duplicate) that analysis.
- Return ONLY a JSON array of 4 strings, no other text. All questions must be in English.

Example format:
["What is the current IV rank vs historical for {symbol}?", "Are there upcoming earnings or catalyst dates for {symbol}?", "What are analyst price targets for {symbol}?", "What is the sector sentiment for {symbol}?"]

Return the JSON array:"""

            planning_response = await self._call_gemini_with_search(
                planning_prompt, use_search=False, model_override=model_override
            )
            
            # Validate planning response
            if not planning_response or not isinstance(planning_response, str):
                logger.warning("Planning response is empty or invalid. Using default questions.")
                planning_response = ""
            
            # Parse questions
            try:
                # Clean JSON if wrapped in markdown
                cleaned = re.sub(r"```json\s*|\s*```", "", planning_response).strip()
                questions = json.loads(cleaned)
                if not isinstance(questions, list):
                    raise ValueError("Response is not a list")
                if len(questions) != 4:
                    logger.warning(f"Expected 4 questions, got {len(questions)}. Using first 4.")
                    questions = questions[:4]
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse planning questions: {e}. Using defaults.")
                questions = [
                    f"What is the current IV rank vs historical for {symbol}?",
                    f"Are there upcoming earnings or catalyst dates for {symbol}?",
                    f"What are analyst price targets for {symbol}?",
                    f"What is the current sector sentiment for {symbol}?",
                ]
            
            update_progress(15, f"Generated {len(questions)} research questions")

            # ========== STEP 2: RESEARCH PHASE (parallel) ==========
            research_findings: list[dict[str, Any]] = []
            total_questions = len(questions)

            if total_questions == 0:
                logger.error("No research questions generated. Using default questions.")
                questions = [
                    f"What is the current IV rank vs historical for {symbol}?",
                    f"Are there upcoming earnings or catalyst dates for {symbol}?",
                    f"What are analyst price targets for {symbol}?",
                    f"What is the current sector sentiment for {symbol}?",
                ]
                total_questions = len(questions)

            async def _research_one(idx: int, question: str) -> dict[str, Any]:
                if not question or not isinstance(question, str):
                    return {"question": str(question), "findings": "[Invalid question]"}
                research_prompt = f"""Research this specific question: "{question}"

Use Google Search to find current, factual information.
Summarize your findings with specific facts, numbers, dates, and data points. Write in English only.
Be concise but comprehensive.

Question: {question}
Research Summary:"""
                try:
                    research_response = await self._call_gemini_with_search(
                        research_prompt, use_search=True, model_override=model_override
                    )
                    if not research_response or not isinstance(research_response, str):
                        research_response = "[Research response was empty or invalid]"
                    return {"question": question, "findings": research_response}
                except Exception as e:
                    logger.error(f"Research failed for question {idx + 1}: {e}")
                    return {"question": question, "findings": f"[Research unavailable: {str(e)}]"}

            update_progress(15, f"Researching {total_questions} questions in parallel...")
            tasks = [_research_one(idx, q) for idx, q in enumerate(questions)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    research_findings.append({
                        "question": questions[i] if i < len(questions) else "Unknown",
                        "findings": f"[Research unavailable: {str(r)}]",
                    })
                else:
                    research_findings.append(r)
            update_progress(70, "Research phase completed. Synthesizing final report...")
            
            # ========== STEP 3: SYNTHESIS PHASE ==========
            # Build comprehensive context (safely handle None/empty values)
            research_summary_parts = []
            for r in research_findings:
                if isinstance(r, dict):
                    question = r.get("question", "Unknown question")
                    findings = r.get("findings", "No findings available")
                    research_summary_parts.append(f"Q: {question}\nA: {findings}")
            research_summary = "\n\n".join(research_summary_parts) if research_summary_parts else "No research findings available."
            
            # Extract data for synthesis prompt (same format as regular report)
            # Handle None cases properly
            if not isinstance(strategy_context, dict):
                raise ValueError("strategy_context must be a dictionary in synthesis phase")
            
            legs = strategy_context.get("legs")
            if not isinstance(legs, list):
                legs = []
            
            portfolio_greeks = strategy_context.get("portfolio_greeks")
            if not isinstance(portfolio_greeks, dict):
                portfolio_greeks = {}
            
            strategy_metrics = strategy_context.get("strategy_metrics")
            if not isinstance(strategy_metrics, dict):
                strategy_metrics = {}
            
            trade_execution = strategy_context.get("trade_execution")
            if not isinstance(trade_execution, dict):
                trade_execution = {}
            
            payoff_summary = strategy_context.get("payoff_summary")
            if not isinstance(payoff_summary, dict):
                payoff_summary = {}
            
            legs_json = []
            # Ensure legs is a list and filter out None/invalid entries
            for leg in legs:
                # Skip None or non-dict legs
                if not isinstance(leg, dict):
                    logger.warning(f"Skipping invalid leg in deep research (not a dict): {leg}")
                    continue
                # Safely extract leg fields with type validation
                action = str(leg.get("action", "buy")).upper()
                quantity_raw = leg.get("quantity", 1)
                quantity = int(quantity_raw) if quantity_raw is not None and isinstance(quantity_raw, (int, float)) else 1
                expiry = leg.get("expiry") or leg.get("expiration_date", "N/A")
                if not expiry or not isinstance(expiry, str):
                    expiry = "N/A"
                strike_raw = leg.get("strike", 0)
                strike = float(strike_raw) if strike_raw is not None and isinstance(strike_raw, (int, float)) else 0.0
                option_type = str(leg.get("type", "call")).upper()
                premium_raw = leg.get("premium", 0)
                premium = float(premium_raw) if premium_raw is not None and isinstance(premium_raw, (int, float)) else 0.0
                
                legs_json.append({
                    "action": action,
                    "quantity": quantity,
                    "expiry": expiry,
                    "strike": strike,
                    "type": option_type,
                    "premium": premium,
                })
            
            # Safely extract and convert max_profit and max_loss to float
            max_profit_raw = strategy_metrics.get("max_profit")
            max_profit = float(max_profit_raw) if max_profit_raw is not None and isinstance(max_profit_raw, (int, float)) else 0.0
            max_loss_raw = strategy_metrics.get("max_loss")
            max_loss = float(max_loss_raw) if max_loss_raw is not None and isinstance(max_loss_raw, (int, float)) else 0.0
            
            breakeven_points = strategy_metrics.get("breakeven_points", [])
            if not isinstance(breakeven_points, list):
                breakeven_points = []
            # Filter out None values and ensure all are numbers
            breakeven_points = [float(be) for be in breakeven_points if be is not None and isinstance(be, (int, float))]
            breakevens = ", ".join([f"${be:.2f}" for be in breakeven_points]) if breakeven_points else "N/A"
            
            # Safely extract IV values, filtering out None/invalid legs
            iv_values = []
            for leg in legs:
                if isinstance(leg, dict):
                    # Try to get IV from either field, but check for None explicitly
                    iv = leg.get("implied_volatility")
                    if iv is None:
                        iv = leg.get("implied_vol")
                    # Only append if IV is not None and is a valid number
                    if iv is not None and isinstance(iv, (int, float)) and iv > 0:
                        iv_values.append(float(iv))
            current_iv = sum(iv_values) / len(iv_values) if iv_values else 0
            iv_info = f"{current_iv:.1f}% Absolute" if current_iv > 0 else "N/A"
            
            # Calculate risk/reward ratio safely
            try:
                if max_loss < 0 and max_loss != 0:
                    risk_reward = abs(max_profit / max_loss)
                else:
                    risk_reward = 0
                pop_estimate = min(95, max(5, 50 + (risk_reward - 1) * 15))
            except (ZeroDivisionError, TypeError, ValueError):
                # Fallback if calculation fails
                risk_reward = 0
                pop_estimate = 50  # Default to 50% if calculation fails
            
            strategy_name = strategy_context.get("strategy_name", "Custom Strategy")
            # Ensure spot_price is a number (handle None case)
            spot_price_raw = strategy_context.get("spot_price")
            spot_price = float(spot_price_raw) if spot_price_raw is not None and isinstance(spot_price_raw, (int, float)) else 0.0
            symbol = strategy_context.get("symbol", "N/A")
            expiration_date = strategy_context.get("expiration_date") or strategy_context.get("expiry", "N/A")
            # Current report date (US/Eastern) so memo header shows actual generation time
            report_date_str = _report_date_utc_now()

            # Note: max_profit and max_loss are already converted to float above (lines 1152-1154)
            # No need to convert again here
            
            if use_three_part and agent_summaries is not None and recommended_strategies is not None:
                # Three-part report: use internal_preliminary_report as FOUNDATION, AUGMENT with research
                rec_str = json.dumps(recommended_strategies, indent=2, default=str)[:6000]
                # Prefer full internal preliminary report (Phase A multi-agent synthesis) as foundation
                if internal_preliminary_report and len(internal_preliminary_report) > 200:
                    internal_block = f"""**Internal Team's Preliminary Analysis (MULTI-AGENT SYNTHESIS - USE AS FOUNDATION):**
Below is our internal team's comprehensive analysis from Greeks Analyst, IV Environment Analyst, Market Context Analyst, and Risk Scenario Analyst. This is your FOUNDATION. Do NOT discard or shorten it.

{internal_preliminary_report}

**Additional Agent Detail (if needed for depth):**
{json.dumps({k: v for k, v in (agent_summaries or {}).items() if k not in ("internal_synthesis_full",) and isinstance(v, str)}, indent=2, default=str)[:6000]}"""
                else:
                    internal_block = f"""**Internal Expert Analysis (Greeks, IV, Market, Risk - full analyses):**
{json.dumps(agent_summaries or {}, indent=2, default=str)[:12000]}"""

                synthesis_prompt = f"""You are a Senior Derivatives Strategist. Produce a DEEP, professional investment memo. The report must be IN-DEPTH and DATA-RICH. The entire report must be in English only; do not use Chinese or any other language.

**Report Date (MANDATORY - use this exact date in the memo header; do NOT use 2023, 2024, or any other date):** {report_date_str}

At the very top of the memo, include this header block using the Report Date above exactly:
To: Investment Committee
From: Senior Derivatives Strategist
Date: {report_date_str}
Subject: Investment Memo: {symbol} {strategy_name}

{internal_block}

**External Research Findings (Google Search - PRIMARY SOURCE for facts, dates, numbers):**
{research_summary}

**System-Recommended Strategies (format as Part 3; do NOT regenerate):**
{rec_str}

**User Strategy Context:**
Symbol: {symbol}, Strategy: {strategy_name}, Spot: ${spot_price:.2f}, IV: {iv_info}
Legs: {json.dumps(legs_json, indent=2, default=str)}
Max Profit: ${max_profit:,.2f}, Max Loss: ${max_loss:,.2f}, POP: {pop_estimate:.0f}%, Breakevens: {breakevens}
Net Greeks: Delta {float(portfolio_greeks.get('delta', 0) or 0):.4f}, Theta {float(portfolio_greeks.get('theta', 0) or 0):.4f}, Vega {float(portfolio_greeks.get('vega', 0) or 0):.4f}

**Fundamental Data (FMP):**
{self._format_deep_research_fundamental_context(strategy_context)}

**REQUIRED OUTPUT STRUCTURE (strict order, English only):**

## Executive Summary
[3-5 sentences: key thesis, main risks, recommendation. Be substantive.]

## 1. Fundamentals
[MINIMUM 400 WORDS. Company overview, valuation, key ratios, catalysts (earnings dates etc.), analyst targets with specific numbers, macro/sector context. CITE External Research Findings for dates and numbers. Expand the internal analysis with research-backed specifics. Do not be brief.]

## 2. Your Strategy Review
[MINIMUM 400 WORDS. Greeks interpretation (delta/gamma/theta/vega implications), IV environment, market fit, risk scenarios, worst-case analysis, overall verdict and corrective advice. Use internal multi-agent analysis as base; augment with research. Be thorough.]

## 3. System-Recommended Strategies
[Present the system-recommended strategies above as readable Markdown. Include: strategy name, legs, rationale, scenario, cost/POP. Do NOT invent new strategies.]

**DEPTH REQUIREMENT: Each of sections 1 and 2 must be at least 400 words. The report must feel like a professional hedge fund memo, not a brief summary.**
**LANGUAGE: English only. No Chinese.**
**PRIORITY: External Research provides facts/dates/numbers. Internal analysis provides interpretation. Combine both. If research contradicts internal view, note and give judgment.**
Output Markdown only."""
            else:
                synthesis_prompt = f"""You are a Senior Derivatives Strategist at a top-tier Hedge Fund. Based on the extensive research below, write a professional investment memo in Markdown format. The entire report must be in English only; do not use Chinese or any other language.

**Report Date (MANDATORY - use this exact date in the memo header; do NOT use 2023, 2024, or any other date):** {report_date_str}

At the very top of the memo, include this header block using the Report Date above exactly:
To: Investment Committee
From: Senior Derivatives Strategist
Date: {report_date_str}
Subject: Investment Memo: {symbol} {strategy_name}

**Strategy Context:**
Target Ticker: {symbol}
Strategy Name: {strategy_name}
Current Spot Price: ${spot_price:.2f}
Implied Volatility: {iv_info}

Strategy Structure (Legs):
{json.dumps(legs_json, indent=2, default=str)}

Financial Metrics:
- Max Profit: ${max_profit:,.2f}
- Max Loss: ${max_loss:,.2f}
- Probability of Profit: {pop_estimate:.0f}%
- Breakeven Points: {breakevens}

Net Greeks:
- Delta: {float(portfolio_greeks.get('delta', 0) or 0):.4f}
- Gamma: {float(portfolio_greeks.get('gamma', 0) or 0):.4f}
- Theta: {float(portfolio_greeks.get('theta', 0) or 0):.4f}
- Vega: {float(portfolio_greeks.get('vega', 0) or 0):.4f}

**Research Findings:**
{research_summary}

**Fundamental Data (FMP - valuation, analyst, catalysts, sentiment):**
{self._format_deep_research_fundamental_context(strategy_context)}

**Complete Strategy Summary (JSON format for reference):**
```json
{json.dumps({
    "symbol": symbol,
    "strategy_name": strategy_name,
    "spot_price": spot_price,
    "expiration_date": expiration_date,
    "legs": legs_json,
    "portfolio_greeks": portfolio_greeks,
    "strategy_metrics": {
        "max_profit": max_profit,
        "max_loss": max_loss,
        "breakeven_points": breakeven_points,
    },
    "trade_execution": trade_execution,
    "payoff_summary": payoff_summary,
}, indent=2, default=str)}
```

**Analysis Requirements:**

1. 🌍 Market Context & Grounding
   - Incorporate the research findings above
   - Discuss upcoming catalysts (earnings, events) that match expiration date
   - Analyze IV environment based on research

2. 🛡️ Risk/Reward Stress Test
   - Greeks Analysis: Delta bias, Theta decay, Vega sensitivity, Tail risk
   - Worst Case Scenario: Under what market move does this lose maximum money?

3. ⚖️ Verdict & Score
   - Give a Risk/Reward Score (0-10)
   - Summarize in one bold sentence

**Output Format (Strict Markdown):**

## 📊 Executive Summary

[2-sentence hook summarizing trade logic and key risks]

## 🔍 Market Alignment (Fundamental & IV)

[Discuss how strategy fits current news cycle and volatility environment. Cite research findings.]

## 🛠️ Strategy Mechanics & Greeks

**Structure:** [Explain the legs simply]

**The Edge:** [Where does profit come from?]

**Greeks Exposure:**
- **Delta:** [Bullish/Bearish/Neutral]
- **Theta:** [Daily Burn Rate]
- **Vega:** [Volatility Sensitivity]

## ⚠️ Scenario Analysis (The "What-Ifs")

| Scenario | Stock Price Move | Estimated P&L | Logic |
|----------|------------------|---------------|-------|
| Bull Case | +5% | ... | ... |
| Bear Case | -5% | ... | ... |
| Stagnant | 0% | ... | ... |

## 💡 Final Verdict: [Score]/10

[Final recommendation and specific price levels to watch]

Write the investment memo:"""

            # Synthesis generates long report; allow up to 20 min to avoid ReadTimeout
            final_report = await self._call_gemini_with_search(
                synthesis_prompt,
                use_search=False,
                max_output_tokens=16384,
                timeout_sec=1200,
                model_override=model_override,
            )
            
            # Validate response
            if not final_report or not isinstance(final_report, str):
                raise ValueError("Synthesized report is None or not a string")
            if len(final_report.strip()) < 500:
                raise ValueError(f"Synthesized report too short: {len(final_report)} characters (minimum 500 required)")
            
            update_progress(100, "Deep research report completed")
            
            # When full pipeline (agent_summaries + recommended_strategies), return dict for task_metadata.research_questions (§5.2)
            if use_three_part:
                return {
                    "report": final_report,
                    "research_questions": questions,
                    "full_prompt": synthesis_prompt,
                }
            return final_report
            
        except CircuitBreakerError:
            logger.error("Gemini API circuit breaker is OPEN for deep research")
            raise
        except Exception as e:
            logger.error(f"Deep research report generation failed: {e}", exc_info=True)
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