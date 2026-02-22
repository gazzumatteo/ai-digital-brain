"""Tests for channels/base.py — data models and ChannelPlugin ABC."""

from __future__ import annotations

import asyncio

from digital_brain.channels.base import (
    ChannelPlugin,
    InboundMessage,
    MediaAttachment,
    OutboundResult,
)

# --- Concrete stub for testing the ABC ---


class StubChannel(ChannelPlugin):
    """Minimal concrete implementation for testing."""

    def channel_id(self) -> str:
        return "stub"

    def capabilities(self) -> dict:
        return {"media": True, "commands": False}

    async def start(self, abort_signal: asyncio.Event) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def send_text(self, to, text, **kwargs):
        return OutboundResult(channel="stub", message_id="1", success=True)

    async def send_media(self, to, text, media_url, **kwargs):
        return OutboundResult(channel="stub", message_id="2", success=True)

    async def download_file(self, file_id):
        return b"fake", "image/jpeg"

    async def health_check(self):
        return {"ok": True}

    def normalize_target(self, raw):
        return raw if raw.isdigit() else None


# --- Tests ---


class TestMediaAttachment:
    def test_create_image(self):
        att = MediaAttachment(
            type="image",
            mime_type="image/jpeg",
            file_id="abc123",
            file_size=1024,
            width=800,
            height=600,
        )
        assert att.type == "image"
        assert att.mime_type == "image/jpeg"
        assert att.file_id == "abc123"
        assert att.file_size == 1024
        assert att.duration_seconds is None

    def test_create_audio(self):
        att = MediaAttachment(
            type="audio",
            mime_type="audio/ogg",
            file_id="xyz",
            duration_seconds=12.5,
        )
        assert att.duration_seconds == 12.5
        assert att.width is None

    def test_defaults(self):
        att = MediaAttachment(type="document", mime_type="application/pdf", file_id="f1")
        assert att.file_size is None
        assert att.filename is None
        assert att.caption is None


class TestInboundMessage:
    def test_text_only(self):
        msg = InboundMessage(
            channel="telegram",
            chat_id="123",
            sender_id="456",
            sender_name="Alice",
            text="Hello!",
        )
        assert msg.media == []
        assert msg.reply_to_id is None
        assert msg.thread_id is None
        assert msg.raw is None

    def test_with_media(self):
        att = MediaAttachment(type="image", mime_type="image/png", file_id="f1")
        msg = InboundMessage(
            channel="telegram",
            chat_id="123",
            sender_id="456",
            sender_name="Bob",
            text="Check this photo",
            media=[att],
        )
        assert len(msg.media) == 1
        assert msg.media[0].type == "image"


class TestOutboundResult:
    def test_success(self):
        r = OutboundResult(channel="telegram", message_id="99", success=True)
        assert r.error is None

    def test_failure(self):
        r = OutboundResult(channel="telegram", message_id="", success=False, error="timeout")
        assert not r.success
        assert r.error == "timeout"


class TestChannelPluginABC:
    def test_stub_implements_interface(self):
        ch = StubChannel()
        assert ch.channel_id() == "stub"
        assert ch.capabilities()["media"] is True

    async def test_stub_send_text(self):
        ch = StubChannel()
        result = await ch.send_text("123", "hello")
        assert result.success

    async def test_stub_download_file(self):
        ch = StubChannel()
        data, mime = await ch.download_file("abc")
        assert data == b"fake"
        assert mime == "image/jpeg"

    def test_normalize_target(self):
        ch = StubChannel()
        assert ch.normalize_target("12345") == "12345"
        assert ch.normalize_target("abc") is None
