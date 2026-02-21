"""Daily Picks Service - v5.0 Implementation
按照 Phase 1 Growth Engine v5.0 方案实现每日精选策略生成
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pytz

from app.schemas.strategy_recommendation import Outlook, RiskProfile
from app.services.ai_service import ai_service
from app.services.strategy_engine import StrategyEngine
from app.services.market_data_service import MarketDataService
from app.services.tiger_service import tiger_service
from app.services.cache import cache_service

logger = logging.getLogger(__name__)
EST = pytz.timezone("US/Eastern")


class DailyPicksService:
    """每日精选策略生成服务（v5.0）"""

    def __init__(self):
        self.market_data_service = MarketDataService()
        self.tiger_service = tiger_service
        self.ai_service = ai_service

    async def generate_picks(self) -> List[Dict[str, Any]]:
        """生成每日精选策略 (Multi-Agent Engine)"""
        try:
            # Step 1: Multi-Agent Stock Screening
            criteria = {
                "market_cap": "Large Cap",
                "min_volume": 1500000,
                "earnings_days_ahead": 5,
                "limit": 10
            }
            
            logger.info("Starting Multi-Agent Stock Screening for Daily Picks...")
            ranked_stocks = await self.ai_service.agent_coordinator.coordinate_stock_screening(criteria)
            
            if not ranked_stocks:
                logger.warning("No stocks passed multi-agent screening")
                return []
                
            # Take top 3
            top_3 = ranked_stocks[:3]
            picks = []
            
            for candidate in top_3:
                # Step 2: Strategy Generation
                strategy = await self._build_strategy(candidate)
                if not strategy:
                    continue
                    
                # Step 3: AI Formatting
                ai_analysis = await self._analyze_with_ai(strategy, candidate)
                if ai_analysis:
                    pick = self._normalize_pick_for_frontend(strategy, ai_analysis, candidate)
                    picks.append(pick)

            logger.info(f"Generated {len(picks)} multi-agent daily picks")
            return picks

        except Exception as e:
            logger.error(f"Failed to generate daily picks: {e}", exc_info=True)
            return []

    async def _build_strategy(self, candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Step 2: 策略构建（调用 Tiger API）"""
        symbol = candidate['symbol']
        technical_score = float(candidate.get('technical_score') or 5.0)
        fundamental_score = float(candidate.get('fundamental_score') or 5.0)

        try:
            # 获取下周五到期日
            expiration_date = self._get_next_friday()

            option_chain = await self.tiger_service.get_option_chain(
                symbol=symbol,
                expiration_date=expiration_date,
                is_pro=False,  # 系统任务，使用免费配额
                force_refresh=False  # 使用缓存
            )

            spot_price = option_chain.get('spot_price') or option_chain.get('underlying_price')
            if not spot_price or spot_price <= 0:
                logger.warning(f"No spot price for {symbol}")
                return None

            # 根据 Agent 得分选择 outlook
            if technical_score >= 7.0 and fundamental_score >= 6.0:
                outlook = Outlook.BULLISH
            elif technical_score <= 3.0 and fundamental_score <= 4.0:
                outlook = Outlook.BEARISH
            else:
                outlook = Outlook.NEUTRAL

            # 使用 StrategyEngine 生成策略
            engine = StrategyEngine(market_data_service=self.market_data_service)

            strategies = engine.generate_strategies(
                chain=option_chain,
                symbol=symbol,
                spot_price=float(spot_price),
                outlook=outlook,
                risk_profile=RiskProfile.CONSERVATIVE,
                capital=10000.0,
                expiration_date=expiration_date
            )

            if strategies:
                # 返回第一个策略
                strategy = strategies[0]
                return {
                    'symbol': symbol,
                    'strategy_name': strategy.name,
                    'legs': [leg.dict() if hasattr(leg, 'dict') else leg.model_dump() for leg in strategy.legs],
                    'metrics': strategy.metrics.dict() if hasattr(strategy.metrics, 'dict') else strategy.metrics.model_dump(),
                    'expiration_date': expiration_date,
                    'spot_price': spot_price,
                    'outlook': outlook.value
                }
            else:
                logger.warning(f"No strategies generated for {symbol}")
                return None

        except Exception as e:
            logger.error(f"Failed to build strategy for {symbol}: {e}", exc_info=True)
            return None

    def _normalize_pick_for_frontend(
        self, strategy: Dict[str, Any], ai_analysis: Dict[str, Any], candidate: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build a single pick with all fields the frontend expects (headline, analysis, max_profit, max_loss, etc.)."""
        metrics = strategy.get("metrics") or {}
        mp = metrics.get("max_profit")
        max_profit = float(mp) if isinstance(mp, (int, float)) else 0.0
        ml = metrics.get("max_loss")
        max_loss = float(ml) if isinstance(ml, (int, float)) else 0.0
        breakeven = metrics.get("breakeven_points") or metrics.get("breakeven") or []

        outlook_raw = (strategy.get("outlook") or "NEUTRAL").upper()
        if outlook_raw == "BULLISH":
            outlook_display = "Bullish"
        elif outlook_raw == "BEARISH":
            outlook_display = "Bearish"
        else:
            outlook_display = "Neutral"

        reasoning = (ai_analysis.get("reasoning") or "").strip() or "AI analysis unavailable"
        headline = (ai_analysis.get("headline") or "").strip() or f"{strategy.get('symbol', '')} {strategy.get('strategy_name', 'Strategy')}"
        analysis = (ai_analysis.get("analysis") or "").strip() or reasoning
        risks = (ai_analysis.get("risks") or "").strip() or "Standard options risk. Max loss limited to premium paid."

        return {
            "symbol": strategy.get("symbol", ""),
            "strategy_type": strategy.get("strategy_name", ""),
            "strategy_name": strategy.get("strategy_name", ""),
            "strategy": {
                "legs": strategy.get("legs", []),
                "metrics": metrics,
                "expiration_date": strategy.get("expiration_date"),
                "spot_price": strategy.get("spot_price"),
            },
            "legs": strategy.get("legs", []),
            "outlook": outlook_display,
            "risk_level": (ai_analysis.get("risk_level") or "Medium").replace("Unknown", "Medium"),
            "headline": headline,
            "analysis": analysis,
            "risks": risks,
            "target_price": str(ai_analysis.get("target_price", "") or ""),
            "timeframe": str(strategy.get("expiration_date", "") or ""),
            "max_profit": max_profit,
            "max_loss": max_loss,
            "breakeven": breakeven if isinstance(breakeven, list) else [],
            "expiration_date": strategy.get("expiration_date"),
            "spot_price": strategy.get("spot_price"),
            "confidence_score": float(ai_analysis.get("confidence_score") or 0),
            "expected_return_pct": float(ai_analysis.get("expected_return_pct") or 0),
        }

    def _get_next_friday(self) -> str:
        """获取下周五到期日"""
        today = datetime.now(EST).date()
        days_until_friday = (4 - today.weekday()) % 7
        if days_until_friday == 0:
            days_until_friday = 7
        next_friday = today + timedelta(days=days_until_friday)
        return next_friday.strftime("%Y-%m-%d")

    async def _analyze_with_ai(self, strategy: Dict[str, Any], candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """AI 分析（使用 Gemini）"""
        # 检查缓存
        today = datetime.now(EST).date().isoformat()
        cache_key = f"daily_pick_ai_v2:{strategy['symbol']}:{today}"
        cached = await cache_service.get(cache_key)
        if cached:
            logger.debug(f"Using cached AI analysis for {strategy['symbol']}")
            return cached

        try:
            # 构建 Prompt（JSON Mode）
            prompt = f"""
Context: Stock {strategy['symbol']} was selected by our Multi-Agent Engine.
Agent Scores - Composite: {candidate.get('composite_score', 'N/A')}, Fundamental: {candidate.get('fundamental_score', 'N/A')}, Technical: {candidate.get('technical_score', 'N/A')}.
Assigned Outlook: {strategy.get('outlook', 'NEUTRAL')}
Strategy recommended: {strategy['strategy_name']}.
Expiration date: {strategy.get('expiration_date', 'Unknown')}
Spot price: ${strategy.get('spot_price', 0):.2f}
Max profit: ${strategy['metrics'].get('max_profit', 0):.2f}
Max loss: ${abs(strategy['metrics'].get('max_loss', 0)):.2f}

Task: Provide a short, user-facing analysis for this daily pick. Output strictly valid JSON with:
- headline: One short line (e.g. "Bull Call Spread on MU with positive technical momentum") for the card title.
- analysis: 2-3 sentences for the card body: why this stock was picked (fundamental/technical), why this strategy fits the outlook, and key upside/catalyst or risk in plain language.
- reasoning: Same as analysis (for backward compatibility).
- risks: One sentence on main risk (e.g. "Max loss if price moves against; earnings before expiry.").
- risk_level: "Low" or "Medium" or "High" based on max loss vs capital.
- confidence_score: 1-10 number.
- target_price: Optional price target or empty string.
Output only valid JSON, no markdown:
{{
  "strategy_name": "{strategy['strategy_name']}",
  "risk_level": "Medium",
  "expected_return_pct": {strategy['metrics'].get('max_profit', 0) / 100 if strategy['metrics'].get('max_profit') else 0},
  "headline": "One short headline for the pick",
  "analysis": "2-3 sentences explaining why this stock and strategy.",
  "reasoning": "Same as analysis.",
  "risks": "One sentence on main risk.",
  "confidence_score": 8.0,
  "target_price": ""
}}
"""

            # 调用 AI（直接获取干净的 JSON）
            provider = self.ai_service._get_provider()
            
            # 使用 generate_text_response
            ai_response = await provider.generate_text_response(
                prompt=prompt,
                system_prompt="You are an expert options strategist. You must output only valid JSON without any markdown code blocks.",
            )
            
            # 清理可能的 markdown 标记
            cleaned = re.sub(r"```json\s*|\s*```", "", ai_response).strip()
            result = json.loads(cleaned)

            # 缓存结果（24 小时）
            await cache_service.set(cache_key, result, ttl=86400)

            return result

        except Exception as e:
            logger.error(f"AI analysis failed for {strategy['symbol']}: {e}", exc_info=True)
            metrics = strategy.get("metrics") or {}
            return {
                "strategy_name": strategy["strategy_name"],
                "risk_level": "Medium",
                "expected_return_pct": (metrics.get("max_profit") or 0) / 100,
                "headline": f"{strategy['symbol']} {strategy['strategy_name']}",
                "analysis": "Analysis temporarily unavailable. Strategy was selected by our multi-agent screening.",
                "reasoning": "AI analysis unavailable",
                "risks": "Standard options risk. Do not invest more than you can afford to lose.",
                "confidence_score": 0.0,
                "target_price": "",
            }


# 保持向后兼容的全局函数
async def generate_daily_picks_pipeline() -> list[dict[str, Any]]:
    """
    生成每日精选（向后兼容函数）
    
    使用新的 DailyPicksService 实现
    """
    service = DailyPicksService()
    return await service.generate_picks()
