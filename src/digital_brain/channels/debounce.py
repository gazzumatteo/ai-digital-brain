"""Inbound message debouncer — coalesces rapid consecutive messages."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from digital_brain.channels.base import InboundMessage

logger = logging.getLogger(__name__)


@dataclass
class _BufferEntry:
    """Buffered messages waiting to be flushed."""

    messages: list[InboundMessage] = field(default_factory=list)
    timer: asyncio.TimerHandle | None = None


class InboundDebouncer:
    """Coalesces rapid consecutive messages from the same sender.

    When a user sends 5 messages in quick succession, without debouncing the
    AI would generate 5 separate responses.  The debouncer buffers messages
    keyed by ``(channel, chat_id, sender_id)`` and flushes them as a single
    combined message after *debounce_ms* of silence.

    Parameters
    ----------
    debounce_ms:
        Milliseconds to wait after the last message before flushing.
    on_flush:
        Async callback invoked with the coalesced ``InboundMessage``.
    """

    def __init__(
        self,
        debounce_ms: int = 1500,
        on_flush: Callable[[InboundMessage], Awaitable[None]] | None = None,
    ) -> None:
        self._debounce_s = debounce_ms / 1000.0
        self._on_flush = on_flush
        self._buffer: dict[str, _BufferEntry] = {}

    @staticmethod
    def _build_key(msg: InboundMessage) -> str:
        return f"{msg.channel}:{msg.chat_id}:{msg.sender_id}"

    async def enqueue(self, message: InboundMessage) -> None:
        """Add a message to the debounce buffer.

        If a previous message from the same sender in the same chat is already
        buffered, the timer is reset.  When the timer finally fires the
        buffered messages are coalesced and flushed.
        """
        key = self._build_key(message)
        entry = self._buffer.get(key)

        if entry is None:
            entry = _BufferEntry()
            self._buffer[key] = entry
        elif entry.timer is not None:
            entry.timer.cancel()

        entry.messages.append(message)

        loop = asyncio.get_running_loop()
        entry.timer = loop.call_later(
            self._debounce_s,
            lambda k=key: asyncio.ensure_future(self._flush(k)),
        )

    async def _flush(self, key: str) -> None:
        """Coalesce buffered messages and invoke on_flush."""
        entry = self._buffer.pop(key, None)
        if entry is None or not entry.messages:
            return

        combined = self._coalesce(entry.messages)
        logger.info(
            "Debounce flush: key=%s messages=%d",
            key,
            len(entry.messages),
        )

        if self._on_flush is not None:
            await self._on_flush(combined)

    async def flush_all(self) -> None:
        """Immediately flush all buffered messages (e.g. on shutdown)."""
        keys = list(self._buffer.keys())
        for key in keys:
            entry = self._buffer.get(key)
            if entry and entry.timer:
                entry.timer.cancel()
            await self._flush(key)

    @staticmethod
    def _coalesce(messages: list[InboundMessage]) -> InboundMessage:
        """Merge multiple messages into one.

        - Texts are joined with newlines.
        - Media attachments are concatenated.
        - Metadata comes from the *last* message (most recent).
        """
        last = messages[-1]
        combined_text = "\n".join(m.text for m in messages if m.text)
        combined_media = []
        for m in messages:
            combined_media.extend(m.media)

        return InboundMessage(
            channel=last.channel,
            chat_id=last.chat_id,
            sender_id=last.sender_id,
            sender_name=last.sender_name,
            text=combined_text,
            media=combined_media,
            reply_to_id=last.reply_to_id,
            thread_id=last.thread_id,
            raw=last.raw,
        )
