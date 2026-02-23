"""Media processor — downloads, validates and converts media for the AI layer."""

from __future__ import annotations

import fnmatch
import logging
from typing import TYPE_CHECKING, Any

from digital_brain.channels.base import MediaAttachment

if TYPE_CHECKING:
    from digital_brain.channels.base import ChannelPlugin

logger = logging.getLogger(__name__)

# Defaults — override via MediaSettings in config
DEFAULT_MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
DEFAULT_ALLOWED_TYPES = [
    "image/*",
    "audio/*",
    "video/*",
    "application/pdf",
]


class MediaValidationError(Exception):
    """Raised when a media attachment fails validation."""


class MediaProcessor:
    """Downloads media from a channel and converts them to ADK-compatible parts.

    The processor validates file size and MIME type before downloading, then
    converts the binary data into ``google.genai.types.Part`` objects that can
    be passed to a multimodal LLM via Google ADK.
    """

    def __init__(
        self,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
        allowed_types: list[str] | None = None,
    ) -> None:
        self._max_file_size_bytes = max_file_size_bytes
        self._allowed_types = allowed_types or DEFAULT_ALLOWED_TYPES

    def _is_mime_allowed(self, mime_type: str) -> bool:
        """Check if a MIME type matches the allowlist (supports wildcards)."""
        for pattern in self._allowed_types:
            if fnmatch.fnmatch(mime_type, pattern):
                return True
        return False

    def validate(self, attachment: MediaAttachment) -> None:
        """Validate a media attachment before downloading.

        Raises MediaValidationError if validation fails.
        """
        if not self._is_mime_allowed(attachment.mime_type):
            raise MediaValidationError(
                f"MIME type '{attachment.mime_type}' is not allowed. Allowed: {self._allowed_types}"
            )
        if attachment.file_size is not None and attachment.file_size > self._max_file_size_bytes:
            max_mb = self._max_file_size_bytes / (1024 * 1024)
            raise MediaValidationError(
                f"File size {attachment.file_size} bytes exceeds limit of {max_mb:.0f} MB"
            )

    async def download(
        self, channel: ChannelPlugin, attachment: MediaAttachment
    ) -> tuple[bytes, str]:
        """Download a media file from the channel.

        Returns (file_bytes, mime_type).  Validates the attachment before
        downloading.
        """
        self.validate(attachment)
        data, mime_type = await channel.download_file(attachment.file_id)

        # Post-download size check (file_size may not have been known beforehand)
        if len(data) > self._max_file_size_bytes:
            max_mb = self._max_file_size_bytes / (1024 * 1024)
            raise MediaValidationError(
                f"Downloaded file ({len(data)} bytes) exceeds limit of {max_mb:.0f} MB"
            )

        return data, mime_type

    def to_adk_part(self, data: bytes, mime_type: str) -> Any:
        """Convert raw bytes into a ``google.genai.types.Part``.

        Gemini natively supports: image/*, audio/*, video/*, application/pdf.
        """
        from google.genai import types

        return types.Part.from_bytes(data=data, mime_type=mime_type)

    async def process_attachments(
        self, channel: ChannelPlugin, attachments: list[MediaAttachment]
    ) -> list[Any]:
        """Download, validate and convert a list of attachments to ADK parts.

        Skips individual attachments that fail validation (logs a warning) so
        that one bad file doesn't block the entire message.
        """
        parts: list[Any] = []
        for att in attachments:
            try:
                data, mime_type = await self.download(channel, att)
                parts.append(self.to_adk_part(data, mime_type))
                logger.debug(
                    "Processed media: type=%s mime=%s size=%d",
                    att.type,
                    mime_type,
                    len(data),
                )
            except MediaValidationError as exc:
                logger.warning("Skipping media attachment: %s", exc)
            except Exception:
                logger.exception("Failed to process media attachment: %s", att.file_id)
        return parts
