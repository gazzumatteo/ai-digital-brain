"""Tests for channels/pipeline.py — InboundPipeline."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from digital_brain.channels.base import (
    ChannelPlugin,
    InboundMessage,
    MediaAttachment,
    OutboundResult,
)
from digital_brain.channels.debounce import InboundDebouncer
from digital_brain.channels.media import MediaProcessor
from digital_brain.channels.pipeline import InboundPipeline
from digital_brain.channels.security import DmPolicyEnforcer


class FakeChannel(ChannelPlugin):
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def channel_id(self) -> str:
        return "test"

    def capabilities(self) -> dict:
        return {}

    async def start(self, abort_signal):
        pass

    async def stop(self):
        pass

    async def send_text(self, to, text, **kwargs):
        self.sent.append((to, text))
        return OutboundResult(channel="test", message_id="1", success=True)

    async def send_media(self, to, text, media_url, **kwargs):
        return OutboundResult(channel="test", message_id="2", success=True)

    async def download_file(self, file_id):
        return b"bytes", "image/jpeg"

    async def health_check(self):
        return {"ok": True}

    def normalize_target(self, raw):
        return raw


def _msg(text: str = "hello", sender: str = "user1") -> InboundMessage:
    return InboundMessage(
        channel="test",
        chat_id="chat1",
        sender_id=sender,
        sender_name="Test",
        text=text,
    )


class TestInboundPipeline:
    async def test_text_message_dispatched(self):
        dispatch = AsyncMock(return_value="AI says hi")
        channel = FakeChannel()

        pipeline = InboundPipeline(
            security=DmPolicyEnforcer(policy="open"),
            debouncer=InboundDebouncer(debounce_ms=50),
            media_processor=MediaProcessor(),
            dispatch_fn=dispatch,
        )

        await pipeline.process(channel, _msg("hello"))
        # Wait for debounce flush
        await asyncio.sleep(0.1)

        dispatch.assert_called_once()
        args = dispatch.call_args
        assert args[0][1] == "hello"  # text
        assert args[0][2] == []  # no media parts

        # Response sent back
        assert len(channel.sent) == 1
        assert channel.sent[0][1] == "AI says hi"

    async def test_blocked_by_security(self):
        dispatch = AsyncMock(return_value="should not be called")
        channel = FakeChannel()

        pipeline = InboundPipeline(
            security=DmPolicyEnforcer(policy="disabled"),
            debouncer=InboundDebouncer(debounce_ms=50),
            media_processor=MediaProcessor(),
            dispatch_fn=dispatch,
        )

        await pipeline.process(channel, _msg("hello"))
        await asyncio.sleep(0.1)

        dispatch.assert_not_called()
        assert len(channel.sent) == 0

    async def test_pairing_blocks_unknown(self):
        dispatch = AsyncMock(return_value="response")
        channel = FakeChannel()

        pipeline = InboundPipeline(
            security=DmPolicyEnforcer(policy="pairing"),
            debouncer=InboundDebouncer(debounce_ms=50),
            media_processor=MediaProcessor(),
            dispatch_fn=dispatch,
        )

        await pipeline.process(channel, _msg("hello"))
        await asyncio.sleep(0.1)

        dispatch.assert_not_called()

    async def test_media_message_skips_debounce(self):
        dispatch = AsyncMock(return_value="I see your photo")
        channel = FakeChannel()

        pipeline = InboundPipeline(
            security=DmPolicyEnforcer(policy="open"),
            debouncer=InboundDebouncer(debounce_ms=5000),  # very long debounce
            media_processor=MediaProcessor(),
            dispatch_fn=dispatch,
        )

        msg = InboundMessage(
            channel="test",
            chat_id="chat1",
            sender_id="user1",
            sender_name="Test",
            text="check this",
            media=[MediaAttachment(type="image", mime_type="image/jpeg", file_id="f1")],
        )

        with patch.object(
            pipeline._media_processor, "process_attachments", return_value=["adk_part"]
        ):
            await pipeline.process(channel, msg)

        # Should have dispatched immediately (no debounce wait)
        await asyncio.sleep(0.05)
        dispatch.assert_called_once()
        assert dispatch.call_args[0][2] == ["adk_part"]  # media_parts

    async def test_custom_user_id_resolver(self):
        dispatch = AsyncMock(return_value="hi")
        channel = FakeChannel()

        async def resolve(ch: str, sender: str) -> str:
            return f"brain_{sender}"

        pipeline = InboundPipeline(
            security=DmPolicyEnforcer(policy="open"),
            debouncer=InboundDebouncer(debounce_ms=50),
            media_processor=MediaProcessor(),
            dispatch_fn=dispatch,
            resolve_user_id=resolve,
        )

        await pipeline.process(channel, _msg("hello"))
        await asyncio.sleep(0.1)

        # user_id should be resolved via our custom function
        assert dispatch.call_args[0][0] == "brain_user1"

    async def test_dispatch_error_sends_fallback(self):
        dispatch = AsyncMock(side_effect=RuntimeError("AI crashed"))
        channel = FakeChannel()

        pipeline = InboundPipeline(
            security=DmPolicyEnforcer(policy="open"),
            debouncer=InboundDebouncer(debounce_ms=50),
            media_processor=MediaProcessor(),
            dispatch_fn=dispatch,
        )

        await pipeline.process(channel, _msg("hello"))
        await asyncio.sleep(0.1)

        # Should still send an error message back
        assert len(channel.sent) == 1
        assert "errore" in channel.sent[0][1].lower() or "dispiace" in channel.sent[0][1].lower()

    async def test_long_response_chunked(self):
        long_response = "A" * 8000
        dispatch = AsyncMock(return_value=long_response)
        channel = FakeChannel()

        pipeline = InboundPipeline(
            security=DmPolicyEnforcer(policy="open"),
            debouncer=InboundDebouncer(debounce_ms=50),
            media_processor=MediaProcessor(),
            dispatch_fn=dispatch,
            chunk_limit=4096,
        )

        await pipeline.process(channel, _msg("hello"))
        await asyncio.sleep(0.1)

        # Should have sent multiple chunks
        assert len(channel.sent) >= 2
        combined = "".join(text for _, text in channel.sent)
        assert len(combined) == 8000
