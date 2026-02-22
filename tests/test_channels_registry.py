"""Tests for channels/registry.py — ChannelRegistry lifecycle."""

from __future__ import annotations

import asyncio

import pytest

from digital_brain.channels.base import ChannelPlugin, OutboundResult
from digital_brain.channels.registry import ChannelRegistry


class FakeChannel(ChannelPlugin):
    def __init__(self, cid: str = "fake") -> None:
        self._cid = cid
        self.started = False
        self.stopped = False

    def channel_id(self) -> str:
        return self._cid

    def capabilities(self) -> dict:
        return {}

    async def start(self, abort_signal: asyncio.Event) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def send_text(self, to, text, **kwargs):
        return OutboundResult(channel=self._cid, message_id="1", success=True)

    async def send_media(self, to, text, media_url, **kwargs):
        return OutboundResult(channel=self._cid, message_id="2", success=True)

    async def download_file(self, file_id):
        return b"", "application/octet-stream"

    async def health_check(self):
        return {"ok": True}

    def normalize_target(self, raw):
        return raw


class TestChannelRegistry:
    def test_register_and_get(self):
        reg = ChannelRegistry()
        ch = FakeChannel("telegram")
        reg.register(ch)
        assert reg.get("telegram") is ch

    def test_register_duplicate_raises(self):
        reg = ChannelRegistry()
        reg.register(FakeChannel("telegram"))
        with pytest.raises(ValueError, match="already registered"):
            reg.register(FakeChannel("telegram"))

    def test_get_unknown_raises(self):
        reg = ChannelRegistry()
        with pytest.raises(KeyError, match="not registered"):
            reg.get("nonexistent")

    def test_list_channels(self):
        reg = ChannelRegistry()
        assert reg.list_channels() == []
        reg.register(FakeChannel("a"))
        reg.register(FakeChannel("b"))
        assert sorted(reg.list_channels()) == ["a", "b"]

    def test_unregister(self):
        reg = ChannelRegistry()
        reg.register(FakeChannel("x"))
        reg.unregister("x")
        assert reg.list_channels() == []

    def test_unregister_nonexistent_is_noop(self):
        reg = ChannelRegistry()
        reg.unregister("nope")  # should not raise

    async def test_start_all(self):
        reg = ChannelRegistry()
        ch1 = FakeChannel("a")
        ch2 = FakeChannel("b")
        reg.register(ch1)
        reg.register(ch2)

        abort = asyncio.Event()
        await reg.start_all(abort)
        assert ch1.started
        assert ch2.started

    async def test_stop_all(self):
        reg = ChannelRegistry()
        ch1 = FakeChannel("a")
        ch2 = FakeChannel("b")
        reg.register(ch1)
        reg.register(ch2)

        await reg.stop_all()
        assert ch1.stopped
        assert ch2.stopped

    async def test_health_check_all(self):
        reg = ChannelRegistry()
        reg.register(FakeChannel("a"))
        reg.register(FakeChannel("b"))

        results = await reg.health_check_all()
        assert results["a"]["ok"] is True
        assert results["b"]["ok"] is True

    async def test_start_all_empty(self):
        reg = ChannelRegistry()
        await reg.start_all(asyncio.Event())  # should not raise
