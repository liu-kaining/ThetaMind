"""Alpha Radar: scan market movers and push Telegram alerts."""

import logging
from typing import Any

from app.core.config import settings
from app.services.telegram_service import telegram_service
from app.services.tiger_service import tiger_service

logger = logging.getLogger(__name__)

# Minimum |change_percent| to consider as "big move" (filter out small moves)
MIN_MOVE_PCT = 5.0


def _base_url() -> str:
    base = (settings.domain or "").strip()
    if not base:
        return "https://thetamind.ai"
    if not base.startswith("http"):
        return f"https://{base}"
    return base.rstrip("/")


def _format_alert(symbol: str, change_percent: float, price: float | None) -> str:
    direction = "暴涨" if change_percent >= 0 else "暴跌"
    price_str = f"${price:.2f}" if price is not None and price > 0 else "N/A"
    link = f"{_base_url()}/company-data?symbol={symbol}"
    return (
        f"🚨 **【AlphaEdge 异动雷达】** 🔥 标的：**{symbol}** 异动{direction} {change_percent:+.2f}%!\n"
        f"📊 现价：{price_str}\n\n"
        "🤖 华尔街机构正在行动！资金流向已发生偏移。\n"
        f"👉 [立即点击，使用 AI 财务法医进行排雷，并一键生成高胜率期权防御策略]({link})"
    )


async def scan_and_alert() -> None:
    """
    Scan US top gainers/losers, filter by |change%| >= 5%, build FOMO-style
    Markdown and send via Telegram. Never raises; failures are logged.
    """
    if not telegram_service.is_configured:
        logger.debug("Radar: Telegram not configured. Skip scan_and_alert.")
        return

    try:
        # Fetch top gainers and top losers (limit 3 each; we filter by MIN_MOVE_PCT)
        gainers: list[dict[str, Any]] = []
        losers: list[dict[str, Any]] = []

        try:
            raw_gainers = await tiger_service.get_market_scanner(
                market="US",
                criteria="top_gainers",
                limit=10,
            )
            for s in raw_gainers[:10]:
                pct = s.get("change_percent")
                if pct is not None and float(pct) >= MIN_MOVE_PCT:
                    gainers.append(s)
                    if len(gainers) >= 3:
                        break
        except Exception as e:
            logger.warning("Radar: top_gainers scan failed: %s", e, exc_info=True)

        try:
            raw_losers = await tiger_service.get_market_scanner(
                market="US",
                criteria="top_losers",
                limit=10,
            )
            for s in raw_losers[:10]:
                pct = s.get("change_percent")
                if pct is not None and float(pct) <= -MIN_MOVE_PCT:
                    losers.append(s)
                    if len(losers) >= 3:
                        break
        except Exception as e:
            logger.warning("Radar: top_losers scan failed: %s", e, exc_info=True)

        sent = 0
        for s in gainers:
            symbol = (s.get("symbol") or "").upper()
            if not symbol:
                continue
            change_pct = s.get("change_percent")
            price = s.get("price")
            if change_pct is None:
                continue
            try:
                change_f = float(change_pct)
            except (TypeError, ValueError):
                continue
            text = _format_alert(symbol, change_f, float(price) if price is not None else None)
            await telegram_service.send_markdown_message(text)
            sent += 1

        for s in losers:
            symbol = (s.get("symbol") or "").upper()
            if not symbol:
                continue
            change_pct = s.get("change_percent")
            price = s.get("price")
            if change_pct is None:
                continue
            try:
                change_f = float(change_pct)
            except (TypeError, ValueError):
                continue
            text = _format_alert(symbol, change_f, float(price) if price is not None else None)
            await telegram_service.send_markdown_message(text)
            sent += 1

        if sent > 0:
            logger.info("Radar: sent %d Telegram alert(s).", sent)
        else:
            logger.debug("Radar: no movers above threshold or scan failed.")
    except Exception as e:
        logger.warning("Radar scan_and_alert error (non-fatal): %s", e, exc_info=True)


