"""Stock Ranking Agent - AI-driven stock ranking for Daily Picks."""

import json
import logging
import re
from typing import Any, Dict, List

from app.services.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.ai.base import BaseAIProvider

logger = logging.getLogger(__name__)


class StockRankingAgent(BaseAgent):
    """Stock Ranking Agent - Uses AI to rank stocks from fundamental + technical analysis.

    Ranking is done by the AI (not rule-based average). AI receives full analysis
    text and scores, and outputs a structured ranked list with composite scores and reasons.
    """

    def __init__(self, name: str, ai_provider: BaseAIProvider, dependencies: Dict[str, Any]):
        super().__init__(
            name=name,
            agent_type=AgentType.RECOMMENDATION,
            ai_provider=ai_provider,
            dependencies=dependencies,
        )

    def _get_role_prompt(self) -> str:
        return """You are a Stock Ranking Specialist for an options strategy platform.

Your job is to rank candidate stocks for daily options strategy picks. You receive
fundamental and technical analysis (and scores) for each symbol. You must:

1. Synthesize fundamental + technical analysis and decide which stocks are best for
   options strategies (consider: liquidity, volatility, clarity of trend, catalyst).
2. Output a strict JSON object with a single key "ranked_stocks", whose value is an
   array of objects, one per symbol, in order from best to worst. Each object must have:
   - "symbol": string (ticker)
   - "composite_score": number 0-10 (your overall score)
   - "fundamental_score": number 0-10 (from or consistent with the health_score given)
   - "technical_score": number 0-10 (from or consistent with the technical_score given)
   - "reason": string (1-2 sentences why this rank)

Output only valid JSON. No markdown, no code fences."""

    async def execute(self, context: AgentContext) -> AgentResult:
        try:
            analysis_results = context.input_data.get("analysis_results", [])
            if not analysis_results:
                return AgentResult(
                    agent_name=self.name,
                    agent_type=self.agent_type,
                    success=False,
                    data={},
                    error="analysis_results not provided in context",
                )

            prompt = self._build_ranking_prompt(analysis_results)
            expected_symbols = {r.get("candidate", {}).get("symbol") for r in analysis_results if r.get("candidate", {}).get("symbol")}

            ranked_stocks = await self._get_ai_ranking(prompt, context, expected_symbols, analysis_results)
            ranking_analysis = "AI ranking used for daily picks."

            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=True,
                data={
                    "analysis": ranking_analysis,
                    "ranked_stocks": ranked_stocks,
                    "top_recommendations": ranked_stocks[:3] if len(ranked_stocks) >= 3 else ranked_stocks,
                    "total_ranked": len(ranked_stocks),
                },
            )
        except Exception as e:
            logger.error(f"StockRankingAgent execution failed: {e}", exc_info=True)
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=False,
                data={},
                error=str(e),
            )

    def _build_ranking_prompt(self, analysis_results: List[Dict[str, Any]]) -> str:
        """Build prompt with full analysis context so AI can reason."""
        return f"""Rank these stocks for daily options strategy picks. Best first.

{self._format_analysis_results(analysis_results)}

Output a JSON object with exactly one key "ranked_stocks": an array of objects in rank order (best first). Each object must have: "symbol", "composite_score" (0-10), "fundamental_score" (0-10), "technical_score" (0-10), "reason" (short string). Include every symbol listed above. Output only valid JSON, no markdown."""

    async def _get_ai_ranking(
        self,
        prompt: str,
        context: AgentContext,
        expected_symbols: set,
        analysis_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Call AI with json_mode, parse ranked list; fallback to rule-based if parse fails."""
        try:
            if hasattr(self.ai_provider, "generate_text_response"):
                raw = await self.ai_provider.generate_text_response(
                    prompt=prompt,
                    system_prompt=self._role_prompt,
                )
            else:
                raw = await self._call_ai(prompt, system_prompt=self._role_prompt, context=context)
            cleaned = re.sub(r"```json\s*|\s*```", "", (raw or "").strip())
            data = json.loads(cleaned)
            arr = data.get("ranked_stocks") if isinstance(data, dict) else None
            if not isinstance(arr, list) or len(arr) == 0:
                raise ValueError("AI did not return ranked_stocks array")
            seen = set()
            ranked = []
            for i, item in enumerate(arr):
                if not isinstance(item, dict):
                    continue
                sym = (item.get("symbol") or "").strip().upper()
                if not sym or sym in seen:
                    continue
                seen.add(sym)
                composite = item.get("composite_score")
                if composite is None and "composite_score" in item:
                    composite = 5.0
                if not isinstance(composite, (int, float)):
                    composite = 5.0
                fundamental = item.get("fundamental_score")
                if fundamental is not None and not isinstance(fundamental, (int, float)):
                    fundamental = None
                technical = item.get("technical_score")
                if technical is not None and not isinstance(technical, (int, float)):
                    technical = None
                ranked.append({
                    "symbol": sym,
                    "composite_score": round(float(composite), 1),
                    "fundamental_score": round(float(fundamental), 1) if fundamental is not None else None,
                    "technical_score": round(float(technical), 1) if technical is not None else None,
                    "reason": str(item.get("reason") or "").strip() or None,
                    "rank": 0,
                })
            for sym in (expected_symbols or set()):
                if sym and sym not in seen:
                    ranked.append({
                        "symbol": sym,
                        "composite_score": 5.0,
                        "fundamental_score": None,
                        "technical_score": None,
                        "reason": None,
                        "rank": 0,
                    })
            for i, s in enumerate(ranked):
                s["rank"] = i + 1
            return ranked
        except Exception as e:
            logger.warning("AI ranking parse failed, using rule-based fallback: %s", e)
            return self._calculate_composite_scores(analysis_results)
    
    def _format_analysis_results(self, analysis_results: List[Dict[str, Any]]) -> str:
        """Format analysis results for the ranking AI (scores + analysis text)."""
        lines = []
        for i, result in enumerate(analysis_results):
            candidate = result.get("candidate", {})
            analysis = result.get("analysis", {})
            symbol = candidate.get("symbol", f"Stock_{i}")
            lines.append(f"\n--- {symbol} ---")
            fundamental = analysis.get("fundamental_analyst") or {}
            technical = analysis.get("technical_analyst") or {}
            if isinstance(fundamental, dict):
                health_score = fundamental.get("health_score")
                if health_score is not None:
                    lines.append(f"  Fundamental score: {health_score}/10")
                text = fundamental.get("analysis")
                if isinstance(text, str) and text.strip():
                    summary = text.strip()[:500] + ("..." if len(text.strip()) > 500 else "")
                    lines.append(f"  Fundamental analysis: {summary}")
            if isinstance(technical, dict):
                technical_score = technical.get("technical_score")
                if technical_score is not None:
                    lines.append(f"  Technical score: {technical_score}/10")
                text = technical.get("analysis")
                if isinstance(text, str) and text.strip():
                    summary = text.strip()[:500] + ("..." if len(text.strip()) > 500 else "")
                    lines.append(f"  Technical analysis: {summary}")
        return "\n".join(lines) if lines else "No analysis results available"
    
    def _calculate_composite_scores(self, analysis_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate composite scores and rank stocks.
        
        Args:
            analysis_results: List of analysis result dictionaries
            
        Returns:
            List of ranked stocks with composite scores
        """
        scored_stocks = []
        
        for result in analysis_results:
            candidate = result.get("candidate", {})
            analysis = result.get("analysis", {})
            
            symbol = candidate.get("symbol", "UNKNOWN")
            
            # Calculate composite score
            scores = []
            
            # Fundamental score
            fundamental = analysis.get("fundamental_analyst") or {}
            if isinstance(fundamental, dict):
                health_score = fundamental.get("health_score")
                if health_score is not None and isinstance(health_score, (int, float)):
                    scores.append(float(health_score) / 10.0)  # Convert to 0-1 scale
            
            # Technical score
            technical = analysis.get("technical_analyst") or {}
            if isinstance(technical, dict):
                technical_score = technical.get("technical_score")
                if technical_score is not None and isinstance(technical_score, (int, float)):
                    scores.append(float(technical_score) / 10.0)  # Convert to 0-1 scale
            
            # Calculate average (or weighted average)
            if scores:
                composite_score = sum(scores) / len(scores) * 10.0  # Convert back to 0-10
            else:
                composite_score = 5.0  # Default neutral
            
            scored_stocks.append({
                "symbol": symbol,
                "composite_score": round(composite_score, 1),
                "fundamental_score": fundamental.get("health_score") if isinstance(fundamental, dict) and fundamental else None,
                "technical_score": technical.get("technical_score") if isinstance(technical, dict) and technical else None,
                "reason": None,
                "rank": 0,
            })
        scored_stocks.sort(key=lambda x: x["composite_score"], reverse=True)
        for i, stock in enumerate(scored_stocks):
            stock["rank"] = i + 1
        return scored_stocks
