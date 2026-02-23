"""Inbound message handlers — normalizes Telegram updates to InboundMessage."""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from telegram import Message, PhotoSize, Update

from digital_brain.channels.base import InboundMessage, MediaAttachment

logger = logging.getLogger(__name__)

# Text fragment reassembly constants (from OpenClaw pattern)
TEXT_FRAGMENT_THRESHOLD_CHARS = 4000
TEXT_FRAGMENT_MAX_GAP_MS = 1500
TEXT_FRAGMENT_MAX_PARTS = 12

# Media group buffering
MEDIA_GROUP_TIMEOUT_MS = 500


def extract_sender_name(message: Message) -> str:
    """Build a display name from a Telegram message sender."""
    user = message.from_user
    if user is None:
        return "Unknown"
    parts = [user.first_name or "", user.last_name or ""]
    name = " ".join(p for p in parts if p).strip()
    return name or user.username or str(user.id)


def extract_media_attachment(message: Message) -> MediaAttachment | None:
    """Extract a MediaAttachment from a Telegram message, if any media is present."""
    if message.photo:
        # Pick the highest-resolution photo
        photo: PhotoSize = message.photo[-1]
        return MediaAttachment(
            type="image",
            mime_type="image/jpeg",  # Telegram always compresses to JPEG
            file_id=photo.file_id,
            file_size=photo.file_size,
            width=photo.width,
            height=photo.height,
            caption=message.caption,
        )

    if message.voice:
        v = message.voice
        return MediaAttachment(
            type="voice",
            mime_type=v.mime_type or "audio/ogg",
            file_id=v.file_id,
            file_size=v.file_size,
            duration_seconds=float(v.duration) if v.duration else None,
            caption=message.caption,
        )

    if message.audio:
        a = message.audio
        return MediaAttachment(
            type="audio",
            mime_type=a.mime_type or "audio/mpeg",
            file_id=a.file_id,
            file_size=a.file_size,
            duration_seconds=float(a.duration) if a.duration else None,
            filename=a.file_name,
            caption=message.caption,
        )

    if message.video:
        vid = message.video
        return MediaAttachment(
            type="video",
            mime_type=vid.mime_type or "video/mp4",
            file_id=vid.file_id,
            file_size=vid.file_size,
            duration_seconds=float(vid.duration) if vid.duration else None,
            width=vid.width,
            height=vid.height,
            caption=message.caption,
        )

    if message.video_note:
        vn = message.video_note
        return MediaAttachment(
            type="video",
            mime_type="video/mp4",
            file_id=vn.file_id,
            file_size=vn.file_size,
            duration_seconds=float(vn.duration) if vn.duration else None,
            width=vn.length,
            height=vn.length,
            caption=message.caption,
        )

    if message.document:
        doc = message.document
        return MediaAttachment(
            type="document",
            mime_type=doc.mime_type or "application/octet-stream",
            file_id=doc.file_id,
            file_size=doc.file_size,
            filename=doc.file_name,
            caption=message.caption,
        )

    if message.sticker:
        stk = message.sticker
        return MediaAttachment(
            type="sticker",
            mime_type="image/webp",
            file_id=stk.file_id,
            file_size=stk.file_size,
            width=stk.width,
            height=stk.height,
            caption=stk.emoji,
        )

    return None


def normalize_update(update: Update) -> InboundMessage | None:
    """Convert a Telegram Update into a normalized InboundMessage.

    Returns None for updates that are not user messages (e.g. edits,
    service messages, etc.).
    """
    message = update.message
    if message is None:
        return None

    # Skip service messages
    if message.from_user is None:
        return None

    text = message.text or message.caption or ""
    sender_name = extract_sender_name(message)

    media: list[MediaAttachment] = []
    attachment = extract_media_attachment(message)
    if attachment is not None:
        media.append(attachment)

    chat_type = message.chat.type
    is_group = chat_type in ("group", "supergroup")

    return InboundMessage(
        channel="telegram",
        chat_id=str(message.chat_id),
        sender_id=str(message.from_user.id),
        sender_name=sender_name,
        text=text,
        media=media,
        reply_to_id=str(message.reply_to_message.message_id) if message.reply_to_message else None,
        thread_id=str(message.message_thread_id) if message.message_thread_id else None,
        raw={
            "update_id": update.update_id,
            "message_id": message.message_id,
            "chat_type": chat_type,
            "is_group": is_group,
            "media_group_id": message.media_group_id,
        },
    )


class MediaGroupBuffer:
    """Buffers media group updates and flushes them as a single InboundMessage.

    When a user sends an album (multiple photos/videos), Telegram delivers
    them as separate updates sharing the same ``media_group_id``.  This buffer
    collects them and flushes after a short timeout.
    """

    def __init__(self, timeout_ms: int = MEDIA_GROUP_TIMEOUT_MS) -> None:
        self._timeout_s = timeout_ms / 1000.0
        self._groups: dict[str, list[InboundMessage]] = {}
        self._timers: dict[str, asyncio.TimerHandle] = {}
        self._on_flush: Callable[[InboundMessage], Awaitable[None]] | None = None

    def set_flush_callback(self, callback: Callable[[InboundMessage], Awaitable[None]]) -> None:
        self._on_flush = callback

    async def add(self, media_group_id: str, message: InboundMessage) -> None:
        """Add a message to the media group buffer."""
        if media_group_id in self._timers:
            self._timers[media_group_id].cancel()

        self._groups.setdefault(media_group_id, []).append(message)

        loop = asyncio.get_running_loop()
        self._timers[media_group_id] = loop.call_later(
            self._timeout_s,
            lambda gid=media_group_id: asyncio.ensure_future(self._flush(gid)),
        )

    async def _flush(self, media_group_id: str) -> None:
        messages = self._groups.pop(media_group_id, [])
        self._timers.pop(media_group_id, None)

        if not messages:
            return

        # Sort by message_id for consistent ordering
        messages.sort(key=lambda m: m.raw.get("message_id", 0) if m.raw else 0)

        # Combine: first message's text + all media from all messages
        first = messages[0]
        combined_media: list[MediaAttachment] = []
        for msg in messages:
            combined_media.extend(msg.media)

        combined = InboundMessage(
            channel=first.channel,
            chat_id=first.chat_id,
            sender_id=first.sender_id,
            sender_name=first.sender_name,
            text=first.text,
            media=combined_media,
            reply_to_id=first.reply_to_id,
            thread_id=first.thread_id,
            raw=first.raw,
        )

        logger.debug(
            "Media group flushed: group=%s messages=%d media=%d",
            media_group_id,
            len(messages),
            len(combined_media),
        )

        if self._on_flush is not None:
            await self._on_flush(combined)


def is_bot_mentioned(message: Message, bot_username: str) -> bool:
    """Check if the bot is mentioned in a group message."""
    if not bot_username:
        return False

    # Check @mention in text
    text = message.text or message.caption or ""
    if f"@{bot_username}" in text:
        return True

    # Check entities for mention
    entities = message.entities or message.caption_entities or []
    for entity in entities:
        if entity.type == "mention":
            mention_text = text[entity.offset : entity.offset + entity.length]
            if mention_text.lower() == f"@{bot_username.lower()}":
                return True

    # Check if message is a reply to the bot
    if message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.username == bot_username:
            return True

    return False


def is_command(text: str) -> bool:
    """Check if the text is a bot command (starts with /)."""
    return bool(text) and text.startswith("/")


def parse_command(text: str) -> tuple[str, str]:
    """Parse a command into (command_name, args).

    Examples:
        "/start" -> ("start", "")
        "/help" -> ("help", "")
        "/forget all" -> ("forget", "all")
    """
    if not text or not text.startswith("/"):
        return "", text

    parts = text.split(None, 1)
    command = parts[0].lstrip("/").split("@")[0]  # Remove @botname suffix
    args = parts[1] if len(parts) > 1 else ""
    return command, args
