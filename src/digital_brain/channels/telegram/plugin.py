"""TelegramChannel — ChannelPlugin implementation for the Telegram Bot API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, filters

from digital_brain.channels.base import ChannelPlugin, InboundMessage, OutboundResult
from digital_brain.channels.telegram.handlers import (
    MediaGroupBuffer,
    is_bot_mentioned,
    is_command,
    normalize_update,
    parse_command,
)
from digital_brain.channels.telegram.send import send_media_message, send_text_message

logger = logging.getLogger(__name__)


class TelegramChannel(ChannelPlugin):
    """Telegram Bot API integration via python-telegram-bot.

    Supports both webhook and polling modes.

    Parameters
    ----------
    bot_token:
        Telegram Bot API token from @BotFather.
    webhook_url:
        Public URL for receiving webhook updates.  If empty, uses polling mode.
    webhook_secret:
        Shared secret for verifying webhook requests.
    on_message:
        Async callback invoked with ``(TelegramChannel, InboundMessage)`` for
        each incoming user message.
    on_command:
        Async callback invoked with ``(TelegramChannel, str, str, InboundMessage)``
        for bot commands.  Arguments are (channel, command, args, message).
    """

    def __init__(
        self,
        bot_token: str,
        webhook_url: str = "",
        webhook_secret: str = "",
        on_message: Any = None,
        on_command: Any = None,
    ) -> None:
        self._bot_token = bot_token
        self._webhook_url = webhook_url
        self._webhook_secret = webhook_secret
        self._on_message = on_message
        self._on_command = on_command

        self._app: Application | None = None
        self._bot: Bot | None = None
        self._bot_username: str = ""
        self._media_group_buffer = MediaGroupBuffer()
        self._media_group_buffer.set_flush_callback(self._dispatch_message)
        self._running = False

    def channel_id(self) -> str:
        return "telegram"

    def capabilities(self) -> dict[str, Any]:
        return {
            "chat_types": ["private", "group", "supergroup"],
            "media": ["image", "audio", "video", "voice", "document", "sticker"],
            "commands": True,
            "threads": True,
            "reactions": False,
            "polls": False,
        }

    @property
    def bot(self) -> Bot:
        """Return the underlying Bot instance."""
        if self._bot is None:
            raise RuntimeError("TelegramChannel not started")
        return self._bot

    @property
    def bot_username(self) -> str:
        return self._bot_username

    async def start(self, abort_signal: asyncio.Event) -> None:
        """Start the Telegram bot (webhook or polling)."""
        builder = Application.builder().token(self._bot_token)
        self._app = builder.build()
        self._bot = self._app.bot

        # Fetch bot info to know our username
        bot_info = await self._bot.get_me()
        self._bot_username = bot_info.username or ""
        logger.info("Telegram bot started: @%s", self._bot_username)

        # Register a catch-all message handler
        self._app.add_handler(MessageHandler(filters.ALL, self._handle_update))

        await self._app.initialize()

        if self._webhook_url:
            await self._start_webhook(abort_signal)
        else:
            await self._start_polling(abort_signal)

    async def _start_webhook(self, abort_signal: asyncio.Event) -> None:
        """Configure webhook mode (the actual HTTP server is in api/webhooks.py)."""
        await self._app.bot.set_webhook(
            url=self._webhook_url,
            secret_token=self._webhook_secret or None,
        )
        self._running = True
        logger.info("Telegram webhook set: %s", self._webhook_url)
        # In webhook mode, we don't block here — FastAPI handles HTTP.
        # Just wait for the abort signal.
        await abort_signal.wait()

    async def _start_polling(self, abort_signal: asyncio.Event) -> None:
        """Start long-polling for updates."""
        self._running = True

        # Explicitly delete any stale webhook before polling
        try:
            result = await self._bot.delete_webhook(drop_pending_updates=True)
            logger.info("delete_webhook result: %s", result)
        except Exception:
            logger.exception("Failed to delete webhook")

        await self._app.start()

        # Register a global error handler so PTB errors aren't silent
        async def _error_handler(update: object, context: Any) -> None:
            logger.error("PTB error: %s (update=%s)", context.error, update)

        self._app.add_error_handler(_error_handler)

        # --- RAW API TEST: call getUpdates directly to see if Telegram responds ---
        logger.info("Testing raw getUpdates (waiting 5s for a message)…")
        try:
            test_updates = await self._bot.get_updates(timeout=5)
            logger.info("Raw getUpdates returned %d update(s)", len(test_updates))
            for u in test_updates:
                logger.info(
                    "  update_id=%s text=%s",
                    u.update_id,
                    u.message.text[:50] if u.message and u.message.text else "(no text)",
                )
        except Exception:
            logger.exception("Raw getUpdates FAILED")

        await self._app.updater.start_polling(
            drop_pending_updates=False,  # we already cleared above
            allowed_updates=Update.ALL_TYPES,
        )
        logger.info(
            "Telegram polling started — app.running=%s updater.running=%s",
            self._app.running,
            self._app.updater.running if self._app.updater else "no updater",
        )
        await abort_signal.wait()
        logger.info("Telegram polling stopping…")
        await self._app.updater.stop()
        await self._app.stop()

    async def stop(self) -> None:
        """Stop the Telegram bot and clean up."""
        self._running = False
        if self._app is not None:
            if self._webhook_url:
                try:
                    await self._app.bot.delete_webhook()
                except Exception:
                    logger.warning("Failed to delete webhook", exc_info=True)
            await self._app.shutdown()
            logger.info("Telegram bot stopped")

    async def _handle_update(self, update: Update, context: Any) -> None:
        """Process an incoming Telegram update."""
        logger.info(
            "RAW update received: update_id=%s has_message=%s",
            update.update_id,
            update.message is not None,
        )
        message = normalize_update(update)
        if message is None:
            logger.warning("normalize_update returned None for update_id=%s", update.update_id)
            return

        logger.info(
            "Received message: chat=%s sender=%s text=%s",
            message.chat_id,
            message.sender_id,
            message.text[:80] if message.text else "(no text)",
        )

        raw = message.raw or {}
        is_group = raw.get("is_group", False)

        # In groups, only respond if mentioned or if it's a command
        if is_group and update.message:
            if not is_bot_mentioned(update.message, self._bot_username):
                if not is_command(message.text):
                    return

        # Handle commands
        if is_command(message.text):
            command, args = parse_command(message.text)
            if self._on_command is not None:
                try:
                    await self._on_command(self, command, args, message)
                except Exception:
                    logger.exception("Command handler error: /%s", command)
            return

        # Handle media groups (albums)
        media_group_id = raw.get("media_group_id")
        if media_group_id:
            await self._media_group_buffer.add(media_group_id, message)
            return

        # Regular message — dispatch directly
        await self._dispatch_message(message)

    async def _dispatch_message(self, message: InboundMessage) -> None:
        """Forward a message to the on_message callback."""
        if self._on_message is not None:
            try:
                await self._on_message(self, message)
            except Exception:
                logger.exception(
                    "Message dispatch error: chat=%s sender=%s",
                    message.chat_id,
                    message.sender_id,
                )

    async def send_text(self, to: str, text: str, **kwargs: Any) -> OutboundResult:
        """Send a text message to a Telegram chat."""
        results = await send_text_message(
            self.bot,
            chat_id=to,
            text=text,
            reply_to_message_id=kwargs.get("reply_to_id"),
            message_thread_id=kwargs.get("thread_id"),
        )
        # Return the first result (or combine)
        if results:
            return results[0]
        return OutboundResult(
            channel="telegram", message_id="", success=False, error="No chunks sent"
        )

    async def send_media(self, to: str, text: str, media_url: str, **kwargs: Any) -> OutboundResult:
        """Send a media message to a Telegram chat."""
        return await send_media_message(
            self.bot,
            chat_id=to,
            media_url=media_url,
            caption=text,
            reply_to_message_id=kwargs.get("reply_to_id"),
            message_thread_id=kwargs.get("thread_id"),
        )

    async def download_file(self, file_id: str) -> tuple[bytes, str]:
        """Download a file from Telegram by file_id."""
        tg_file = await self.bot.get_file(file_id)
        data = await tg_file.download_as_bytearray()
        # Infer MIME from file path or default
        path = tg_file.file_path or ""
        mime_type = _guess_mime_type(path)
        return bytes(data), mime_type

    async def health_check(self) -> dict[str, Any]:
        """Return health status for the Telegram channel."""
        try:
            me = await self.bot.get_me()
            return {
                "status": "healthy",
                "bot_username": me.username,
                "mode": "webhook" if self._webhook_url else "polling",
            }
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}

    def normalize_target(self, raw: str) -> Optional[str]:
        """Normalize a Telegram chat ID."""
        try:
            int(raw)
            return raw
        except ValueError:
            # Could be a @username — valid target
            if raw.startswith("@"):
                return raw
            return None

    async def process_webhook_update(self, payload: dict[str, Any]) -> None:
        """Process a webhook update from the FastAPI endpoint.

        This is called by the webhook handler when in webhook mode.
        """
        if self._app is None:
            logger.warning("Received webhook update but app is not initialized")
            return

        update = Update.de_json(payload, self._bot)
        if update is not None:
            await self._app.process_update(update)


def _guess_mime_type(file_path: str) -> str:
    """Guess MIME type from a Telegram file path."""
    lower = file_path.lower()
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".ogg") or lower.endswith(".oga"):
        return "audio/ogg"
    if lower.endswith(".mp3"):
        return "audio/mpeg"
    if lower.endswith(".mp4"):
        return "video/mp4"
    if lower.endswith(".pdf"):
        return "application/pdf"
    if lower.endswith(".webm"):
        return "video/webm"
    return "application/octet-stream"
