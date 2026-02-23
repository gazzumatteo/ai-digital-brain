"""Channel plugin abstract base class and shared data models."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class MediaAttachment:
    """A media file attached to an inbound message."""

    type: str
    """Media type: "image", "audio", "video", "document", "voice", "sticker"."""

    mime_type: str
    """MIME type, e.g. "image/jpeg", "audio/ogg", "application/pdf"."""

    file_id: str
    """Channel-specific file identifier (e.g. Telegram file_id)."""

    file_size: int | None = None
    """File size in bytes, if known."""

    filename: str | None = None
    """Original filename, if available."""

    duration_seconds: float | None = None
    """Duration for audio/video, in seconds."""

    width: int | None = None
    """Width in pixels for images/video."""

    height: int | None = None
    """Height in pixels for images/video."""

    caption: str | None = None
    """Caption attached to the media by the sender."""


@dataclass
class InboundMessage:
    """A normalized inbound message from any channel."""

    channel: str
    """Channel identifier, e.g. "telegram"."""

    chat_id: str
    """Unique chat/conversation identifier within the channel."""

    sender_id: str
    """Unique sender identifier within the channel."""

    sender_name: str
    """Human-readable sender display name."""

    text: str
    """Text content of the message (or caption if media-only)."""

    media: list[MediaAttachment] = field(default_factory=list)
    """Media attachments (images, audio, video, documents)."""

    reply_to_id: Optional[str] = None
    """Message ID this is a reply to, if any."""

    thread_id: Optional[str] = None
    """Thread/topic ID for threaded conversations."""

    raw: Any = None
    """Raw event payload from the channel, for debugging."""


@dataclass
class OutboundResult:
    """Result of sending a message to a channel."""

    channel: str
    """Channel the message was sent to."""

    message_id: str
    """Channel-specific ID of the sent message."""

    success: bool
    """Whether the send succeeded."""

    error: Optional[str] = None
    """Error description if success is False."""


class ChannelPlugin(ABC):
    """Abstract base class that every channel integration must implement.

    Encapsulates all channel-specific details (API, auth, message format, target
    IDs) behind a common contract so the AI layer never needs to know which
    channel a message originated from.
    """

    @abstractmethod
    def channel_id(self) -> str:
        """Return the unique identifier for this channel (e.g. "telegram")."""

    @abstractmethod
    def capabilities(self) -> dict[str, Any]:
        """Declare what this channel supports.

        Expected keys: chat_types, reactions, threads, media, commands, polls.
        """

    @abstractmethod
    async def start(self, abort_signal: asyncio.Event) -> None:
        """Start receiving messages (webhook server, polling loop, etc.).

        Must respect *abort_signal* for graceful shutdown.
        """

    @abstractmethod
    async def stop(self) -> None:
        """Stop the channel and release resources."""

    @abstractmethod
    async def send_text(self, to: str, text: str, **kwargs: Any) -> OutboundResult:
        """Send a plain-text (or markdown) message to a chat."""

    @abstractmethod
    async def send_media(self, to: str, text: str, media_url: str, **kwargs: Any) -> OutboundResult:
        """Send a media message (image, file, etc.) with optional caption."""

    @abstractmethod
    async def download_file(self, file_id: str) -> tuple[bytes, str]:
        """Download a file from the channel by its file_id.

        Returns (file_bytes, mime_type).
        """

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Return health/status information for this channel."""

    @abstractmethod
    def normalize_target(self, raw: str) -> Optional[str]:
        """Normalize a raw target identifier to canonical form.

        Returns None if the target is invalid.
        """
