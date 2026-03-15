"""Universal OpenAI-compatible AI provider (DeepSeek, Qwen, etc.)."""

import asyncio
import json
import logging
from typing import Any, Optional

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

DEFAULT_REPORT_PROMPT_TEMPLATE = """# Role Definition

You are a Senior Derivatives Strategist at a top-tier Hedge Fund. Your expertise lies in volatility arbitrage, greeks management, and risk-adjusted returns.
Your tone is professional, objective, insightful, and slightly critical (you don't sugarcoat risks).

# Task

Analyze the provided US Stock Option Strategy based on the Strategy Data and Real-time Market Context.
Produce a comprehensive "Investment Memo" in Markdown format.

# Input Data

Target Ticker: {symbol}
Strategy Name: {strategy_name}
Current Spot Price: ${spot_price}
Implied Volatility (IV): {iv_info}

Strategy Structure (Legs):
{legs_json}

Financial Metrics:
- Max Profit: ${max_profit}
- Max Loss: ${max_loss}
- Probability of Profit (POP): {pop}%
- Breakeven Points: {breakevens}

Net Greeks:
- Delta: {net_delta}
- Gamma: {net_gamma}
- Theta: {net_theta}
- Vega: {net_vega}

# Analysis Requirements (Step-by-Step)

## 1. Market Context & Grounding
Analyze: Is there an upcoming catalyst (Earnings, Fed event, Product launch) that matches the expiration date?
Volatility Check: Is the current IV justified? Is it cheap (buy premiums) or expensive (sell premiums)?

## 2. Risk/Reward Stress Test
Greeks Analysis: Delta, Theta, Vega, Tail Risk.

## 3. Verdict & Score
Give a Risk/Reward Score (0-10). Summarize in one bold sentence.

# Output Format (Strict Markdown)

## Executive Summary
## Market Alignment (Fundamental & IV)
## Strategy Mechanics & Greeks
## Scenario Analysis (The "What-Ifs")
## Final Verdict: [Score]/10
"""

universal_openai_circuit_breaker = CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
)


class UniversalOpenAIProvider(BaseAIProvider):
    """OpenAI-compatible provider for text/reports (DeepSeek, Qwen, etc.)."""

    def __init__(self) -> None:
        base_url = (settings.ai_base_url or "").strip()
        api_key = (settings.ai_api_key or "").strip()
        text_model = (settings.ai_text_model or "").strip()
        if not base_url or not api_key or not text_model:
            raise ValueError(
                "AI_BASE_URL, AI_API_KEY, and AI_TEXT_MODEL are required for Universal OpenAI provider"
            )
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=httpx.Timeout(settings.ai_model_timeout + 10, connect=10.0),
        )
        self.model_name = text_model
        logger.info("Universal OpenAI provider configured: base_url=%s, model=%s", base_url, text_model)

    def _ensure_client(self) -> None:
        if not hasattr(self, "client") or self.client is None:
            raise RuntimeError("Universal OpenAI client is not available.")

    def filter_option_chain(
        self, chain_data: dict[str, Any], spot_price: float
    ) -> dict[str, Any]:
        if not spot_price or spot_price <= 0:
            logger.warning("Invalid spot price for filtering. Returning full chain.")
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
        return filtered

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    @universal_openai_circuit_breaker
    async def generate_report(
        self,
        strategy_summary: dict[str, Any] | None = None,
        strategy_data: dict[str, Any] | None = None,
        option_chain: dict[str, Any] | None = None,
        model_override: Optional[str] = None,
        language: Optional[str] = None,
    ) -> str:
        self._ensure_client()
        if strategy_summary:
            strategy_context = dict(strategy_summary)
            if option_chain:
                strategy_context["option_chain"] = option_chain
        elif strategy_data and option_chain:
            spot_price = option_chain.get("spot_price", 0)
            filtered_chain = self.filter_option_chain(option_chain, spot_price)
            strategy_context = {
                "strategy_info": strategy_data,
                "market_context": {"spot_price": spot_price, "filtered_option_chain": filtered_chain},
            }
        else:
            raise ValueError("Either strategy_summary or (strategy_data + option_chain) must be provided")

        legs = strategy_context.get("legs") or []
        legs_json = json.dumps(legs, indent=2, default=str)
        metrics = strategy_context.get("strategy_metrics") or strategy_context.get("metrics") or {}
        pg = strategy_context.get("portfolio_greeks") or {}
        spot_price = float(strategy_context.get("spot_price") or metrics.get("spot_price") or 0)
        format_dict = {
            "symbol": (strategy_context.get("symbol") or "N/A").upper(),
            "strategy_name": str(strategy_context.get("strategy_name") or strategy_context.get("strategy_type") or "Strategy"),
            "spot_price": f"{spot_price:.2f}" if spot_price else "N/A",
            "iv_info": str(strategy_context.get("iv_summary") or metrics.get("iv") or "N/A"),
            "legs_json": legs_json,
            "max_profit": float(metrics.get("max_profit") or 0),
            "max_loss": float(metrics.get("max_loss") or 0),
            "pop": float(metrics.get("probability_of_profit") or metrics.get("pop") or 0),
            "breakevens": ", ".join(str(x) for x in (metrics.get("breakeven_points") or metrics.get("breakeven") or [])),
            "net_delta": float(pg.get("delta") or 0),
            "net_gamma": float(pg.get("gamma") or 0),
            "net_theta": float(pg.get("theta") or 0),
            "net_vega": float(pg.get("vega") or 0),
            "strategy_summary": json.dumps(strategy_context, indent=2, default=str),
        }
        prompt_template = await config_service.get(
            "ai.report_prompt_template",
            default=DEFAULT_REPORT_PROMPT_TEMPLATE,
        )
        try:
            prompt = prompt_template.format(**format_dict)
        except (KeyError, ValueError):
            prompt = f"Analyze the following strategy:\n\n{format_dict['strategy_summary']}"

        if language and (language := (language or "").strip()):
            prompt = f"{prompt}\n\n**Important:** You MUST generate your analysis and response entirely in the requested language: {language}."

        model = (model_override or self.model_name).strip()
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                ),
                timeout=settings.ai_model_timeout,
            )
            if not response or not response.choices or len(response.choices) == 0:
                raise ValueError("Invalid response from API")
            report = response.choices[0].message.content
            if not report or len(report) < 100:
                raise ValueError("AI response too short or empty")
            return report
        except CircuitBreakerError:
            logger.error("Universal OpenAI circuit breaker is OPEN")
            raise
        except asyncio.TimeoutError:
            raise TimeoutError(f"Request timed out after {settings.ai_model_timeout} seconds")
        except Exception as e:
            logger.error("Universal OpenAI report error: %s", e, exc_info=True)
            raise

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    @universal_openai_circuit_breaker
    async def generate_text_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_override: Optional[str] = None,
    ) -> str:
        self._ensure_client()
        model = (model_override or self.model_name).strip()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                ),
                timeout=settings.ai_model_timeout,
            )
            if not response or not response.choices or len(response.choices) == 0:
                raise ValueError("Invalid response from API")
            result = response.choices[0].message.content
            if not result:
                raise ValueError("Empty response from API")
            return result
        except CircuitBreakerError:
            logger.error("Universal OpenAI circuit breaker is OPEN")
            raise
        except asyncio.TimeoutError:
            raise TimeoutError(f"Request timed out after {settings.ai_model_timeout} seconds")
        except Exception as e:
            logger.error("Universal OpenAI text error: %s", e, exc_info=True)
            raise
