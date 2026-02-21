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
        """生成每日精选策略"""
        try:
            # Step 1: 基础池构建
            candidates = await self._build_base_pool()
            logger.info(f"Base pool: {len(candidates)} candidates")

            if not candidates:
                logger.warning("No candidates found after base pool filtering")
                return []

            # Step 2: 波动率筛选（IV Rank 计算）
            iv_filtered = await self._filter_by_volatility(candidates)
            logger.info(f"After IV filter: {len(iv_filtered)} candidates")

            if not iv_filtered:
                logger.warning("No candidates found after IV filtering")
                return []

            # Step 3: 策略构建（Top 3，调用 Tiger API）
            top_3 = iv_filtered[:3]
            strategies = []
            for candidate in top_3:
                strategy = await self._build_strategy(candidate)
                if strategy:
                    strategies.append(strategy)

            if not strategies:
                logger.warning("No strategies generated")
                return []

            # Step 4: AI 分析
            picks = []
            for strategy in strategies:
                ai_analysis = await self._analyze_with_ai(strategy)
                if ai_analysis:
                    picks.append({
                        **strategy,
                        **ai_analysis
                    })

            logger.info(f"Generated {len(picks)} daily picks")
            return picks

        except Exception as e:
            logger.error(f"Failed to generate daily picks: {e}", exc_info=True)
            # 降级：返回空列表，不崩溃
            return []

    async def _build_base_pool(self) -> List[str]:
        """Step 1: 基础池构建"""
        # 1.1: 从 FinanceDatabase 获取 SP500（本地库，0 IO）
        try:
            # 使用 search_tickers 获取 US Large Cap 股票（近似 SP500）
            symbols = self.market_data_service.search_tickers(
                country="United States",
                market_cap="Large Cap",
                limit=500  # SP500 大约 500 只股票
            )
            logger.info(f"FinanceDatabase: Found {len(symbols)} US Large Cap stocks")
        except Exception as e:
            logger.error(f"Failed to get SP500 from FinanceDatabase: {e}", exc_info=True)
            return []

        if not symbols:
            return []

        # 1.2: 流动性过滤（FMP 批量报价）
        batch_size = 50  # 避免 API 限制
        liquid_symbols = []

        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            try:
                quotes = await self.market_data_service.get_batch_quotes(batch)
                for symbol, quote in quotes.items():
                    volume = quote.get('volume', 0)
                    if volume and volume > 1_500_000:
                        liquid_symbols.append(symbol)
            except Exception as e:
                logger.warning(f"Failed to get batch quotes for batch {i}: {e}")
                continue

        logger.info(f"After liquidity filter (Volume > 1.5M): {len(liquid_symbols)} symbols")

        # 1.3: 事件驱动（Earnings Calendar）
        earnings_symbols = await self._filter_by_earnings(liquid_symbols, days_ahead=5)
        logger.info(f"After earnings filter (next 5 days): {len(earnings_symbols)} symbols")

        return earnings_symbols

    async def _filter_by_earnings(self, symbols: List[str], days_ahead: int = 5) -> List[str]:
        """筛选有 Earnings 的股票"""
        try:
            # 调用 FMP Earnings Calendar
            end_date = (datetime.now(EST) + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
            start_date = datetime.now(EST).strftime("%Y-%m-%d")

            earnings_data = await self.market_data_service._call_fmp_api(
                "earnings-calendar",
                params={
                    "from": start_date,
                    "to": end_date
                }
            )

            if not earnings_data or not isinstance(earnings_data, list):
                logger.warning("No earnings data returned, skipping earnings filter")
                return symbols

            # 提取有 Earnings 的股票代码
            earnings_symbols = set()
            for item in earnings_data:
                symbol = item.get('symbol')
                if symbol:
                    earnings_symbols.add(symbol.upper())

            # 过滤：只保留有 Earnings 的股票
            filtered = [s for s in symbols if s in earnings_symbols]
            return filtered

        except Exception as e:
            logger.warning(f"Failed to filter by earnings: {e}, returning all symbols")
            return symbols

    async def _filter_by_volatility(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Step 2: 波动率筛选（IV Rank 计算）"""
        iv_ranked = []

        for symbol in symbols:
            try:
                # 尝试 A: FinanceToolkit 计算 IV Rank
                iv_rank = await self._calculate_iv_rank_financetoolkit(symbol)

                if iv_rank is None:
                    # 尝试 B: 使用 HV 作为代理
                    iv_rank = await self._calculate_hv_rank(symbol)

                if iv_rank is not None:
                    # 筛选：IV Rank > 60 或 < 20
                    if iv_rank > 60 or iv_rank < 20:
                        iv_ranked.append({
                            'symbol': symbol,
                            'iv_rank': iv_rank
                        })
            except Exception as e:
                logger.warning(f"Failed to calculate IV Rank for {symbol}: {e}")
                continue

        # 排序：按 IV Rank 偏离 50 的程度排序
        iv_ranked.sort(key=lambda x: abs(x['iv_rank'] - 50), reverse=True)

        return iv_ranked

    async def _calculate_iv_rank_financetoolkit(self, symbol: str) -> Optional[float]:
        """尝试 A: 使用 Tiger 期权链的 IV 计算 IV Rank（期权数据来自 Tiger）"""
        try:
            expirations = await self.tiger_service.get_option_expirations(symbol.upper())
            if not expirations or not isinstance(expirations, list):
                return None
            expiration_date = expirations[0] if isinstance(expirations[0], str) else str(expirations[0])
            chain = await self.tiger_service.get_option_chain(
                symbol=symbol.upper(),
                expiration_date=expiration_date,
                is_pro=False,
                force_refresh=False,
            )
            if not chain or not isinstance(chain, dict):
                return None
            ivs: List[float] = []
            for opt_list in (chain.get("calls") or [], chain.get("puts") or []):
                for opt in opt_list or []:
                    if not isinstance(opt, dict):
                        continue
                    iv = opt.get("implied_vol") or opt.get("implied_volatility")
                    g = opt.get("greeks")
                    if iv is None and isinstance(g, dict):
                        iv = g.get("implied_vol") or g.get("implied_volatility")
                    if iv is not None:
                        try:
                            ivs.append(float(iv))
                        except (TypeError, ValueError):
                            pass
            if len(ivs) < 2:
                return None
            ivs_sorted = sorted(ivs)
            current_iv = ivs_sorted[len(ivs_sorted) // 2]
            min_iv, max_iv = min(ivs), max(ivs)
            if max_iv <= min_iv:
                return 50.0
            return float(((current_iv - min_iv) / (max_iv - min_iv)) * 100.0)
        except Exception as e:
            logger.debug(f"Tiger IV Rank calculation failed for {symbol}: {e}")
            return None

    async def _calculate_hv_rank(self, symbol: str) -> Optional[float]:
        """尝试 B: 使用 FMP 历史价格计算 HV Rank（作为 IV 代理）"""
        try:
            return self.market_data_service.get_hv_rank_from_fmp(symbol)
        except Exception as e:
            logger.debug(f"HV Rank calculation failed for {symbol}: {e}")
            return None

    async def _build_strategy(self, candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Step 3: 策略构建（调用 Tiger API）"""
        symbol = candidate['symbol']
        iv_rank = candidate.get('iv_rank', 50)

        try:
            # 获取下周五到期日
            expiration_date = self._get_next_friday()

            # ⚠️ 关键约束：Tiger API 严禁在循环中调用
            # 这里只对 Top 3 调用，不在循环中
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

            # 使用 StrategyEngine 生成策略
            engine = StrategyEngine(market_data_service=self.market_data_service)

            # 根据 IV Rank 选择 outlook
            if iv_rank > 60:
                outlook = Outlook.NEUTRAL  # 高 IV，适合 Iron Condor
            elif iv_rank < 20:
                outlook = Outlook.VOLATILE  # 低 IV，适合 Long Straddle
            else:
                outlook = Outlook.NEUTRAL

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
                    'iv_rank': iv_rank,
                    'expiration_date': expiration_date,
                    'spot_price': spot_price
                }
            else:
                logger.warning(f"No strategies generated for {symbol}")
                return None

        except Exception as e:
            logger.error(f"Failed to build strategy for {symbol}: {e}", exc_info=True)
            return None

    def _get_next_friday(self) -> str:
        """获取下周五到期日"""
        today = datetime.now(EST).date()
        days_until_friday = (4 - today.weekday()) % 7
        if days_until_friday == 0:
            days_until_friday = 7
        next_friday = today + timedelta(days=days_until_friday)
        return next_friday.strftime("%Y-%m-%d")

    async def _analyze_with_ai(self, strategy: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """AI 分析（使用 Gemini 3.0 Pro）"""
        # 检查缓存
        today = datetime.now(EST).date().isoformat()
        cache_key = f"daily_pick_ai:{strategy['symbol']}:{today}"
        cached = await cache_service.get(cache_key)
        if cached:
            logger.debug(f"Using cached AI analysis for {strategy['symbol']}")
            return cached

        try:
            # 构建 Prompt（JSON Mode）
            prompt = f"""
Context: Stock {strategy['symbol']} has IV Rank {strategy.get('iv_rank', 'N/A')} and strategy {strategy['strategy_name']}.
Expiration date: {strategy.get('expiration_date', 'Unknown')}
Spot price: ${strategy.get('spot_price', 0):.2f}
Max profit: ${strategy['metrics'].get('max_profit', 0):.2f}
Max loss: ${abs(strategy['metrics'].get('max_loss', 0)):.2f}

Task: Suggest ONE optimal option strategy and provide analysis.
Output strictly valid JSON:
{{
  "strategy_name": "{strategy['strategy_name']}",
  "risk_level": "Medium",
  "expected_return_pct": {strategy['metrics'].get('max_profit', 0) / 100},
  "reasoning": "Brief explanation in 1 sentence",
  "confidence_score": 8.5
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
            # 降级：返回基础数据，不显示 AI 点评
            return {
                'strategy_name': strategy['strategy_name'],
                'risk_level': 'Unknown',
                'expected_return_pct': strategy['metrics'].get('max_profit', 0) / 100,
                'reasoning': 'AI analysis unavailable',
                'confidence_score': 0.0
            }


# 保持向后兼容的全局函数
async def generate_daily_picks_pipeline() -> list[dict[str, Any]]:
    """
    生成每日精选（向后兼容函数）
    
    使用新的 DailyPicksService 实现
    """
    service = DailyPicksService()
    return await service.generate_picks()
