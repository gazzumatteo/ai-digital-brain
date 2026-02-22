"""Tests for channels/media.py — MediaProcessor."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from digital_brain.channels.base import ChannelPlugin, MediaAttachment, OutboundResult
from digital_brain.channels.media import (
    MediaProcessor,
    MediaValidationError,
)


class FakeChannel(ChannelPlugin):
    """Fake channel that returns configurable file data."""

    def __init__(self, file_data: bytes = b"fake", mime: str = "image/jpeg") -> None:
        self._file_data = file_data
        self._mime = mime

    def channel_id(self) -> str:
        return "fake"

    def capabilities(self) -> dict:
        return {}

    async def start(self, abort_signal):
        pass

    async def stop(self):
        pass

    async def send_text(self, to, text, **kw):
        return OutboundResult(channel="fake", message_id="1", success=True)

    async def send_media(self, to, text, media_url, **kw):
        return OutboundResult(channel="fake", message_id="2", success=True)

    async def download_file(self, file_id):
        return self._file_data, self._mime

    async def health_check(self):
        return {"ok": True}

    def normalize_target(self, raw):
        return raw


class TestMediaProcessorValidation:
    def test_valid_image(self):
        proc = MediaProcessor()
        att = MediaAttachment(type="image", mime_type="image/jpeg", file_id="f1", file_size=1024)
        proc.validate(att)  # should not raise

    def test_valid_audio(self):
        proc = MediaProcessor()
        att = MediaAttachment(type="audio", mime_type="audio/ogg", file_id="f1")
        proc.validate(att)  # should not raise

    def test_valid_pdf(self):
        proc = MediaProcessor()
        att = MediaAttachment(type="document", mime_type="application/pdf", file_id="f1")
        proc.validate(att)  # should not raise

    def test_rejected_mime_type(self):
        proc = MediaProcessor()
        att = MediaAttachment(
            type="document", mime_type="application/x-executable", file_id="f1"
        )
        with pytest.raises(MediaValidationError, match="not allowed"):
            proc.validate(att)

    def test_rejected_zip(self):
        proc = MediaProcessor()
        att = MediaAttachment(type="document", mime_type="application/zip", file_id="f1")
        with pytest.raises(MediaValidationError, match="not allowed"):
            proc.validate(att)

    def test_file_too_large(self):
        proc = MediaProcessor(max_file_size_bytes=1000)
        att = MediaAttachment(
            type="image", mime_type="image/jpeg", file_id="f1", file_size=2000
        )
        with pytest.raises(MediaValidationError, match="exceeds limit"):
            proc.validate(att)

    def test_file_size_unknown_passes_pre_check(self):
        proc = MediaProcessor(max_file_size_bytes=1000)
        att = MediaAttachment(type="image", mime_type="image/jpeg", file_id="f1", file_size=None)
        proc.validate(att)  # should not raise — size check deferred to download

    def test_custom_allowed_types(self):
        proc = MediaProcessor(allowed_types=["text/plain"])
        att = MediaAttachment(type="document", mime_type="text/plain", file_id="f1")
        proc.validate(att)  # should pass

        att2 = MediaAttachment(type="image", mime_type="image/jpeg", file_id="f2")
        with pytest.raises(MediaValidationError):
            proc.validate(att2)


class TestMediaProcessorDownload:
    async def test_download_success(self):
        channel = FakeChannel(file_data=b"image_bytes", mime="image/png")
        proc = MediaProcessor()
        att = MediaAttachment(type="image", mime_type="image/png", file_id="f1")

        data, mime = await proc.download(channel, att)
        assert data == b"image_bytes"
        assert mime == "image/png"

    async def test_download_post_check_size(self):
        """Even if file_size is unknown, reject after download if too large."""
        channel = FakeChannel(file_data=b"x" * 2000, mime="image/jpeg")
        proc = MediaProcessor(max_file_size_bytes=1000)
        att = MediaAttachment(type="image", mime_type="image/jpeg", file_id="f1")

        with pytest.raises(MediaValidationError, match="exceeds limit"):
            await proc.download(channel, att)


class TestMediaProcessorToAdkPart:
    def test_to_adk_part(self):
        proc = MediaProcessor()
        with patch("google.genai.types") as mock_types:
            mock_types.Part.from_bytes.return_value = "mock_part"
            part = proc.to_adk_part(b"data", "image/jpeg")
            assert part == "mock_part"
            mock_types.Part.from_bytes.assert_called_once_with(
                data=b"data", mime_type="image/jpeg"
            )


class TestMediaProcessorProcessAttachments:
    async def test_process_multiple(self):
        channel = FakeChannel(file_data=b"img", mime="image/jpeg")
        proc = MediaProcessor()

        attachments = [
            MediaAttachment(type="image", mime_type="image/jpeg", file_id="f1"),
            MediaAttachment(type="image", mime_type="image/png", file_id="f2"),
        ]

        with patch.object(proc, "to_adk_part", return_value="part"):
            parts = await proc.process_attachments(channel, attachments)
            assert len(parts) == 2
            assert all(p == "part" for p in parts)

    async def test_skips_invalid_attachments(self):
        channel = FakeChannel(file_data=b"data", mime="image/jpeg")
        proc = MediaProcessor()

        attachments = [
            MediaAttachment(type="image", mime_type="image/jpeg", file_id="f1"),
            MediaAttachment(type="document", mime_type="application/x-shellscript", file_id="f2"),
        ]

        with patch.object(proc, "to_adk_part", return_value="part"):
            parts = await proc.process_attachments(channel, attachments)
            # Only the valid image should be processed
            assert len(parts) == 1
