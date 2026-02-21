"""Anomaly Service - v5.0 Implementation
实时异动雷达服务，每 5 分钟扫描期权异动
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pytz

from app.services.market_data_service import MarketDataService
from app.services.tiger_service import tiger_service
from app.services.ai_service import ai_service
from app.services.cache import cache_service

logger = logging.getLogger(__name__)
EST = pytz.timezone("US/Eastern")


class AnomalyService:
    """异动雷达服务"""

    def __init__(self):
        self.market_data_service = MarketDataService()
        self.tiger_service = tiger_service
        self.ai_service = ai_service
        self.use_fmp_unusual_activity = False  # 从验证脚本获取，默认使用兜底方案

    async def detect_anomalies(self) -> List[Dict[str, Any]]:
        """检测异动"""
        try:
            # 策略 A: 尝试使用 FMP Unusual Activity
            if self.use_fmp_unusual_activity:
                anomalies = await self._detect_anomalies_fmp()
            else:
                # 策略 B: 手动计算（兜底）
                anomalies = await self._detect_anomalies_manual()

            # 排序：按分数排序
            anomalies.sort(key=lambda x: x.get('score', 0), reverse=True)

            # 对 Top 1 自动生成 AI 点评
            if anomalies:
                top_anomaly = anomalies[0]
                ai_insight = await self._generate_ai_insight_if_needed(top_anomaly)
                if ai_insight:
                    top_anomaly['ai_insight'] = ai_insight

            return anomalies

        except Exception as e:
            logger.error(f"Failed to detect anomalies: {e}", exc_info=True)
            # 降级：返回空列表，不崩溃
            return []

    async def _detect_anomalies_fmp(self) -> List[Dict[str, Any]]:
        """策略 A: 使用 FMP Unusual Activity"""
        try:
            data = await self.market_data_service._call_fmp_api(
                "stock/option-unusual-activity"
            )

            # 解析 FMP 返回的数据格式
            # 需要根据实际返回格式调整
            anomalies = []
            if isinstance(data, list):
                for item in data:
                    anomalies.append({
                        'symbol': item.get('symbol'),
                        'type': 'unusual_activity',
                        'score': item.get('score', 0),
                        'details': item
                    })
            elif isinstance(data, dict):
                # 如果是单个对象，转换为列表
                anomalies.append({
                    'symbol': data.get('symbol'),
                    'type': 'unusual_activity',
                    'score': data.get('score', 0),
                    'details': data
                })

            return anomalies
        except Exception as e:
            logger.warning(f"FMP unusual activity failed: {e}, falling back to manual")
            return await self._detect_anomalies_manual()

    async def _detect_anomalies_manual(self) -> List[Dict[str, Any]]:
        """策略 B: 手动计算异动（兜底）"""
        anomalies = []

        # 1. 获取最活跃的股票（FMP）
        try:
            active_stocks = await self.market_data_service.get_most_actives()
            if not active_stocks:
                logger.warning("No active stocks found")
                return []
        except Exception as e:
            logger.warning(f"Failed to get most actives: {e}")
            return []

        # 2. 对每个股票获取期权链（Tiger，使用缓存）
        # ⚠️ 关键约束：不在循环中频繁调用 Tiger API
        # 这里限制只检查前 20 个，且使用缓存
        for stock in active_stocks[:20]:
            symbol = stock.get('symbol') if isinstance(stock, dict) else stock
            if not symbol:
                continue

            try:
                # 获取下周五到期日
                expiration_date = self._get_next_friday()

                # 调用 Tiger API（使用缓存）
                option_chain = await self.tiger_service.get_option_chain(
                    symbol=symbol,
                    expiration_date=expiration_date,
                    is_pro=False,
                    force_refresh=False  # 使用缓存，避免频繁调用
                )

                # 3. 计算异动指标
                for option_type in ['calls', 'puts']:
                    options = option_chain.get(option_type, [])
                    for option in options:
                        vol = option.get('volume', 0)
                        oi = option.get('open_interest', 0)

                        # 规则: Vol/OI > 3.0 且 Volume > 2000
                        if oi > 0:
                            vol_oi_ratio = vol / oi
                            if vol_oi_ratio > 3.0 and vol > 2000:
                                # 计算异动分数（转换为整数）
                                score = int(vol_oi_ratio * (vol / 1000))

                                anomalies.append({
                                    'symbol': symbol,
                                    'type': 'volume_surge',
                                    'option_type': option_type,
                                    'strike': option.get('strike'),
                                    'score': score,
                                    'vol_oi_ratio': vol_oi_ratio,
                                    'volume': vol,
                                    'open_interest': oi,
                                    'details': {
                                        'bid': option.get('bid'),
                                        'ask': option.get('ask'),
                                        'iv': option.get('implied_volatility'),
                                    }
                                })
            except Exception as e:
                logger.warning(f"Failed to check {symbol}: {e}")
                continue

        # 去重：每个 symbol 只保留分数最高的异动
        grouped = {}
        for anomaly in anomalies:
            key = f"{anomaly['symbol']}_{anomaly['type']}"
            if key not in grouped or anomaly['score'] > grouped[key]['score']:
                grouped[key] = anomaly

        return list(grouped.values())

    def _get_next_friday(self) -> str:
        """获取下周五到期日"""
        today = datetime.now(EST).date()
        days_until_friday = (4 - today.weekday()) % 7
        if days_until_friday == 0:
            days_until_friday = 7
        next_friday = today + timedelta(days=days_until_friday)
        return next_friday.strftime("%Y-%m-%d")

    async def _generate_ai_insight_if_needed(self, anomaly: Dict[str, Any]) -> Optional[str]:
        """生成 AI 点评（如果需要）"""
        # 检查缓存
        cache_key = f"anomaly_insight:{anomaly['symbol']}:{anomaly['type']}"
        cached = await cache_service.get(cache_key)
        if cached:
            return cached

        # 检查是否应该自动生成（每小时只对 Top 1）
        last_generated_key = f"anomaly_last_generated:{cache_key}"
        last_generated = await cache_service.get(last_generated_key)
        if last_generated:
            # 1 小时内不重复生成
            return None

        try:
            # 生成 AI 点评 (轻量级)
            prompt = f"标的 {anomaly['symbol']} 出现期权异动（{anomaly['type']}）。详情：Volume={anomaly.get('volume', 0)}, OI={anomaly.get('open_interest', 0)}, Vol/OI={anomaly.get('vol_oi_ratio', 0):.2f}。请结合常识给出 50 字以内的专业交易点评。"

            provider = self.ai_service._get_provider()
            ai_response = await provider.generate_text_response(
                prompt=prompt,
                system_prompt="You are a professional options trader. Be extremely concise."
            )

            # 清理换行符，限制长度
            insight = ai_response.replace('\n', ' ').strip()
            if len(insight) > 200:
                insight = insight[:197] + "..."

            # 缓存结果（1 小时）
            await cache_service.set(cache_key, insight, ttl=3600)
            await cache_service.set(last_generated_key, True, ttl=3600)

            return insight

        except Exception as e:
            logger.warning(f"Failed to generate AI insight: {e}")
            return None
