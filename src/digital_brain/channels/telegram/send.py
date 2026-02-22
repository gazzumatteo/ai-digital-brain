"""Outbound messaging — sends responses back to Telegram chats."""

from __future__ import annotations

import logging
from typing import Any

from telegram import Bot
from telegram.constants import ParseMode

from digital_brain.channels.base import OutboundResult
from digital_brain.channels.chunking import ChunkMode, chunk_text

logger = logging.getLogger(__name__)

# Telegram limits
TELEGRAM_TEXT_LIMIT = 4096
TELEGRAM_CAPTION_LIMIT = 1024


async def send_text_message(
    bot: Bot,
    chat_id: str | int,
    text: str,
    *,
    reply_to_message_id: int | None = None,
    message_thread_id: int | None = None,
) -> list[OutboundResult]:
    """Send a text message, chunking if necessary.

    Uses Markdown parse mode.  Falls back to plain text if Markdown parsing
    fails (e.g. unmatched formatting characters).
    """
    chunks = chunk_text(text, limit=TELEGRAM_TEXT_LIMIT, mode=ChunkMode.MARKDOWN)
    results: list[OutboundResult] = []

    for i, chunk in enumerate(chunks):
        # Only reply-to on the first chunk
        reply_id = reply_to_message_id if i == 0 else None
        try:
            msg = await _send_with_fallback(
                bot,
                chat_id=chat_id,
                text=chunk,
                reply_to_message_id=reply_id,
                message_thread_id=message_thread_id,
            )
            results.append(
                OutboundResult(
                    channel="telegram",
                    message_id=str(msg.message_id),
                    success=True,
                )
            )
        except Exception as exc:
            logger.exception("Failed to send Telegram message to %s", chat_id)
            results.append(
                OutboundResult(
                    channel="telegram",
                    message_id="",
                    success=False,
                    error=str(exc),
                )
            )
    return results


async def _send_with_fallback(
    bot: Bot,
    chat_id: str | int,
    text: str,
    reply_to_message_id: int | None = None,
    message_thread_id: int | None = None,
) -> Any:
    """Try sending with Markdown, fall back to plain text on parse error."""
    kwargs: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if reply_to_message_id:
        kwargs["reply_to_message_id"] = reply_to_message_id
    if message_thread_id:
        kwargs["message_thread_id"] = message_thread_id

    try:
        return await bot.send_message(parse_mode=ParseMode.MARKDOWN_V2, **kwargs)
    except Exception:
        # MarkdownV2 failed — try plain Markdown
        try:
            return await bot.send_message(parse_mode=ParseMode.MARKDOWN, **kwargs)
        except Exception:
            # Fall back to no parse mode
            return await bot.send_message(**kwargs)


async def send_media_message(
    bot: Bot,
    chat_id: str | int,
    media_url: str,
    caption: str = "",
    *,
    reply_to_message_id: int | None = None,
    message_thread_id: int | None = None,
) -> OutboundResult:
    """Send a photo/document with optional caption."""
    kwargs: dict[str, Any] = {"chat_id": chat_id}
    if caption:
        kwargs["caption"] = caption[:TELEGRAM_CAPTION_LIMIT]
    if reply_to_message_id:
        kwargs["reply_to_message_id"] = reply_to_message_id
    if message_thread_id:
        kwargs["message_thread_id"] = message_thread_id

    try:
        msg = await bot.send_photo(photo=media_url, **kwargs)
        return OutboundResult(
            channel="telegram",
            message_id=str(msg.message_id),
            success=True,
        )
    except Exception as exc:
        logger.exception("Failed to send Telegram media to %s", chat_id)
        return OutboundResult(
            channel="telegram",
            message_id="",
            success=False,
            error=str(exc),
        )
