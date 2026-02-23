"""Webhook endpoints for channel integrations."""

from __future__ import annotations

import hmac
import logging
from typing import Any, Callable

from fastapi import APIRouter, Header, HTTPException, Request

logger = logging.getLogger(__name__)


def create_webhook_router(
    get_telegram_channel: Callable[[], Any],
    webhook_secret: str = "",
) -> APIRouter:
    """Create a FastAPI router for channel webhook endpoints.

    Parameters
    ----------
    get_telegram_channel:
        Callable that returns the TelegramChannel instance (or None if not
        started yet).
    webhook_secret:
        Shared secret for verifying Telegram webhook requests.  If empty,
        verification is skipped.
    """
    router = APIRouter(prefix="/webhooks", tags=["webhooks"])

    @router.post("/telegram")
    async def telegram_webhook(
        request: Request,
        x_telegram_bot_api_secret_token: str | None = Header(None),
    ) -> dict[str, str]:
        """Receive a webhook update from Telegram."""
        # Verify the secret token if configured
        if webhook_secret:
            if not x_telegram_bot_api_secret_token:
                raise HTTPException(status_code=403, detail="Missing secret token")
            if not hmac.compare_digest(x_telegram_bot_api_secret_token, webhook_secret):
                raise HTTPException(status_code=403, detail="Invalid secret token")

        channel = get_telegram_channel()
        if channel is None:
            raise HTTPException(status_code=503, detail="Telegram channel not initialized")

        try:
            payload = await request.json()
            await channel.process_webhook_update(payload)
        except HTTPException:
            raise
        except Exception:
            logger.exception("Error processing Telegram webhook")
            raise HTTPException(status_code=500, detail="Internal error processing update")

        return {"status": "ok"}

    return router
