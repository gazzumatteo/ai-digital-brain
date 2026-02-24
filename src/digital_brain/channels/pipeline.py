"""Inbound message pipeline — normalizes, secures, and dispatches messages."""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from digital_brain.channels.base import ChannelPlugin, InboundMessage, OutboundResult
from digital_brain.channels.chunking import ChunkMode, chunk_text
from digital_brain.channels.debounce import InboundDebouncer
from digital_brain.channels.media import MediaProcessor
from digital_brain.channels.security import DmPolicyEnforcer

logger = logging.getLogger(__name__)

# Type alias for the AI dispatch function.
# Signature: (user_id, text, media_parts) -> response_text
DispatchFn = Callable[[str, str, list[Any]], Awaitable[str]]


class InboundPipeline:
    """Processes inbound messages from any channel through a standard pipeline.

    Steps:
    1. Security check (DM policy / allowlist)
    2. Debounce (coalesce rapid consecutive messages)
    3. Resolve media (download + convert to ADK parts)
    4. Dispatch to AI
    5. Send response back to channel

    Parameters
    ----------
    security:
        DM policy enforcer instance.
    debouncer:
        Inbound debouncer instance (pipeline wires its own on_flush).
    media_processor:
        Media processor for downloading and converting attachments.
    dispatch_fn:
        Async callable that sends the message to the AI layer.
        Signature: ``(user_id, text, media_parts) -> response_text``.
    resolve_user_id:
        Async callable that maps ``(channel, sender_id)`` to a brain user_id.
        Defaults to using the channel-scoped sender_id directly.
    chunk_limit:
        Max characters per outbound message chunk.
    chunk_mode:
        Chunking mode for outbound messages.
    """

    def __init__(
        self,
        security: DmPolicyEnforcer,
        debouncer: InboundDebouncer,
        media_processor: MediaProcessor,
        dispatch_fn: DispatchFn,
        resolve_user_id: Callable[[str, str], Awaitable[str]] | None = None,
        chunk_limit: int = 4096,
        chunk_mode: ChunkMode = ChunkMode.MARKDOWN,
    ) -> None:
        self._security = security
        self._media_processor = media_processor
        self._dispatch_fn = dispatch_fn
        self._resolve_user_id = resolve_user_id
        self._chunk_limit = chunk_limit
        self._chunk_mode = chunk_mode

        # Wire the debouncer's flush callback to our internal handler
        debouncer._on_flush = self._handle_after_debounce
        self._debouncer = debouncer

        # Channel registry for file downloads — populated by process()
        self._channels: dict[str, ChannelPlugin] = {}

    async def process(self, channel: ChannelPlugin, message: InboundMessage) -> None:
        """Run an inbound message through the full pipeline."""
        cid = channel.channel_id()
        self._channels[cid] = channel

        # 1. Security check
        allowed, reason = self._security.check_access(cid, message.sender_id)
        if not allowed:
            logger.info(
                "Message blocked: channel=%s sender=%s reason=%s",
                cid,
                message.sender_id,
                reason,
            )
            return

        # 2. Debounce — if the message has no media, debounce it.
        #    Messages with media skip debouncing to avoid delays.
        if not message.media:
            await self._debouncer.enqueue(message)
        else:
            await self._handle_after_debounce(message)

    async def _handle_after_debounce(self, message: InboundMessage) -> None:
        """Process a message that has passed security and debouncing."""
        cid = message.channel
        channel = self._channels.get(cid)

        # 3. Resolve media (download + convert to ADK parts)
        media_parts: list[Any] = []
        if message.media and channel is not None:
            media_parts = await self._media_processor.process_attachments(channel, message.media)

        # 4. Resolve user ID
        if self._resolve_user_id is not None:
            user_id = await self._resolve_user_id(cid, message.sender_id)
        else:
            user_id = f"{cid}_{message.sender_id}"

        # 5. Dispatch to AI
        logger.info("Dispatching to AI: user=%s text=%s", user_id, message.text[:80] if message.text else "")
        try:
            response_text = await self._dispatch_fn(user_id, message.text, media_parts)
        except Exception:
            logger.exception(
                "AI dispatch failed: channel=%s chat=%s",
                cid,
                message.chat_id,
            )
            response_text = "Mi dispiace, si è verificato un errore. Riprova più tardi."

        # 6. Send response back to channel
        if channel is not None:
            await self._send_response(channel, message, response_text)

    async def _send_response(
        self, channel: ChannelPlugin, original: InboundMessage, response: str
    ) -> None:
        """Chunk and send the AI response back to the originating channel."""
        chunks = chunk_text(response, limit=self._chunk_limit, mode=self._chunk_mode)

        for chunk in chunks:
            try:
                result: OutboundResult = await channel.send_text(
                    to=original.chat_id,
                    text=chunk,
                    reply_to_id=original.reply_to_id,
                    thread_id=original.thread_id,
                )
                if not result.success:
                    logger.warning(
                        "Failed to send response chunk: channel=%s error=%s",
                        channel.channel_id(),
                        result.error,
                    )
            except Exception:
                logger.exception(
                    "Error sending response: channel=%s chat=%s",
                    channel.channel_id(),
                    original.chat_id,
                )
