"""Telegram push service for Alpha Radar alerts."""

import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Timeout for send message (avoid blocking scheduler)
TELEGRAM_SEND_TIMEOUT = 15.0


class TelegramService:
    """Send Markdown messages to a Telegram chat via Bot API."""

    def __init__(self) -> None:
        self._token: Optional[str] = (
            (settings.telegram_bot_token or "").strip() or None
        )
        self._chat_id: Optional[str] = (
            (settings.telegram_chat_id or "").strip() or None
        )

    @property
    def is_configured(self) -> bool:
        return bool(self._token and self._chat_id)

    async def send_markdown_message(self, text: str) -> None:
        """
        Send a Markdown message to the configured chat.
        Does not raise; logs and returns on failure so the main app never crashes.
        """
        if not self._token or not self._chat_id:
            logger.debug("Telegram not configured (TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing). Skip send.")
            return
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        try:
            async with httpx.AsyncClient(timeout=TELEGRAM_SEND_TIMEOUT) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    # Markdown parse failure — retry without parse_mode
                    if resp.status_code == 400 and "parse" in resp.text.lower():
                        payload_plain = {"chat_id": self._chat_id, "text": text}
                        resp2 = await client.post(url, json=payload_plain)
                        if resp2.status_code == 200:
                            logger.debug("Telegram message sent (plain text fallback).")
                            return
                    logger.warning(
                        "Telegram sendMessage failed: status=%s body=%s",
                        resp.status_code,
                        resp.text[:500],
                    )
                    return
                logger.debug("Telegram message sent successfully.")
        except httpx.TimeoutException as e:
            logger.warning("Telegram send timeout: %s", e)
        except Exception as e:
            logger.warning("Telegram send error (non-fatal): %s", e, exc_info=True)


# Singleton for scheduler and radar to use
telegram_service = TelegramService()
