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
        """尝试 A: 使用 FinanceToolkit 计算 IV Rank"""
        try:
            toolkit = self.market_data_service._get_toolkit([symbol])

            # 获取隐含波动率数据
            iv_data = toolkit.options.get_implied_volatility()

            if iv_data is not None and not iv_data.empty:
                # 计算 IV Rank
                current_iv = float(iv_data.iloc[-1])
                min_52w = float(iv_data.min())
                max_52w = float(iv_data.max())

                if max_52w > min_52w:
                    iv_rank = ((current_iv - min_52w) / (max_52w - min_52w)) * 100
                    return iv_rank

            return None
        except Exception as e:
            logger.debug(f"FinanceToolkit IV Rank calculation failed for {symbol}: {e}")
            return None

    async def _calculate_hv_rank(self, symbol: str) -> Optional[float]:
        """尝试 B: 使用历史波动率作为代理"""
        try:
            toolkit = self.market_data_service._get_toolkit([symbol])

            # 获取历史波动率
            hv_data = toolkit.risk.get_volatility()

            if hv_data is not None and not hv_data.empty:
                # 计算 HV Rank（作为 IV Rank 的代理）
                current_hv = float(hv_data.iloc[-1])
                min_52w = float(hv_data.min())
                max_52w = float(hv_data.max())

                if max_52w > min_52w:
                    hv_rank = ((current_hv - min_52w) / (max_52w - min_52w)) * 100
                    return hv_rank

            return None
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

            # 调用 AI（使用 AIService，Gemini 3.0 Pro）
            # 注意：这里需要调用 AI 生成结构化 JSON
            # 暂时使用 generate_report，然后提取 JSON
            ai_response = await self.ai_service.generate_report(
                strategy_data=strategy,
                option_chain=None  # 不传递完整期权链，节省 token
            )

            # 尝试提取 JSON
            result = self._extract_json_from_response(ai_response, strategy)

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

    def _extract_json_from_response(self, response: str, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """从 AI 响应中提取 JSON（降级方案）"""
        # 尝试提取 JSON 部分
        json_match = re.search(r'\{[^{}]*"strategy_name"[^{}]*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # 如果提取失败，返回默认值
        return {
            'strategy_name': strategy['strategy_name'],
            'risk_level': 'Medium',
            'expected_return_pct': strategy['metrics'].get('max_profit', 0) / 100,
            'reasoning': response[:200] if len(response) > 200 else response,
            'confidence_score': 7.0
        }


# 保持向后兼容的全局函数
async def generate_daily_picks_pipeline() -> list[dict[str, Any]]:
    """
    生成每日精选（向后兼容函数）
    
    使用新的 DailyPicksService 实现
    """
    service = DailyPicksService()
    return await service.generate_picks()
