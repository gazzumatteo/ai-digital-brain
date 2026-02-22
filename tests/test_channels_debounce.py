"""Tests for channels/debounce.py — InboundDebouncer."""

from __future__ import annotations

import asyncio

from digital_brain.channels.base import InboundMessage
from digital_brain.channels.debounce import InboundDebouncer


def _msg(text: str, sender: str = "user1", chat: str = "chat1") -> InboundMessage:
    return InboundMessage(
        channel="test",
        chat_id=chat,
        sender_id=sender,
        sender_name="Test",
        text=text,
    )


class TestInboundDebouncer:
    async def test_single_message_flushes_after_timeout(self):
        flushed: list[InboundMessage] = []

        async def on_flush(msg: InboundMessage) -> None:
            flushed.append(msg)

        debouncer = InboundDebouncer(debounce_ms=50, on_flush=on_flush)
        await debouncer.enqueue(_msg("hello"))

        # Not flushed yet
        assert len(flushed) == 0

        # Wait for the debounce timer
        await asyncio.sleep(0.1)
        assert len(flushed) == 1
        assert flushed[0].text == "hello"

    async def test_rapid_messages_coalesced(self):
        flushed: list[InboundMessage] = []

        async def on_flush(msg: InboundMessage) -> None:
            flushed.append(msg)

        debouncer = InboundDebouncer(debounce_ms=100, on_flush=on_flush)

        await debouncer.enqueue(_msg("hello"))
        await asyncio.sleep(0.02)
        await debouncer.enqueue(_msg("world"))
        await asyncio.sleep(0.02)
        await debouncer.enqueue(_msg("!"))

        # Wait for flush
        await asyncio.sleep(0.2)
        assert len(flushed) == 1
        assert flushed[0].text == "hello\nworld\n!"

    async def test_different_senders_not_coalesced(self):
        flushed: list[InboundMessage] = []

        async def on_flush(msg: InboundMessage) -> None:
            flushed.append(msg)

        debouncer = InboundDebouncer(debounce_ms=50, on_flush=on_flush)

        await debouncer.enqueue(_msg("from alice", sender="alice"))
        await debouncer.enqueue(_msg("from bob", sender="bob"))

        await asyncio.sleep(0.1)
        assert len(flushed) == 2

    async def test_different_chats_not_coalesced(self):
        flushed: list[InboundMessage] = []

        async def on_flush(msg: InboundMessage) -> None:
            flushed.append(msg)

        debouncer = InboundDebouncer(debounce_ms=50, on_flush=on_flush)

        await debouncer.enqueue(_msg("in chat1", chat="c1"))
        await debouncer.enqueue(_msg("in chat2", chat="c2"))

        await asyncio.sleep(0.1)
        assert len(flushed) == 2

    async def test_flush_all(self):
        flushed: list[InboundMessage] = []

        async def on_flush(msg: InboundMessage) -> None:
            flushed.append(msg)

        debouncer = InboundDebouncer(debounce_ms=5000, on_flush=on_flush)

        await debouncer.enqueue(_msg("pending1"))
        await debouncer.enqueue(_msg("pending2", sender="other"))

        # Flush immediately without waiting for timer
        await debouncer.flush_all()
        assert len(flushed) == 2

    async def test_media_in_coalesced_messages(self):
        from digital_brain.channels.base import MediaAttachment

        flushed: list[InboundMessage] = []

        async def on_flush(msg: InboundMessage) -> None:
            flushed.append(msg)

        debouncer = InboundDebouncer(debounce_ms=50, on_flush=on_flush)

        msg1 = _msg("text")
        msg2 = InboundMessage(
            channel="test",
            chat_id="chat1",
            sender_id="user1",
            sender_name="Test",
            text="with photo",
            media=[MediaAttachment(type="image", mime_type="image/jpeg", file_id="f1")],
        )

        await debouncer.enqueue(msg1)
        await asyncio.sleep(0.01)
        await debouncer.enqueue(msg2)

        await asyncio.sleep(0.1)
        assert len(flushed) == 1
        assert len(flushed[0].media) == 1
        assert "text" in flushed[0].text
        assert "with photo" in flushed[0].text

    async def test_no_flush_callback(self):
        """Debouncer without on_flush should not raise."""
        debouncer = InboundDebouncer(debounce_ms=50, on_flush=None)
        await debouncer.enqueue(_msg("orphan"))
        await asyncio.sleep(0.1)  # should complete without error
