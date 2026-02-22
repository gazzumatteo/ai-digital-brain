"""Tests for channels/telegram/plugin.py — TelegramChannel."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from digital_brain.channels.telegram.plugin import TelegramChannel, _guess_mime_type


class TestTelegramChannelBasic:
    def test_channel_id(self):
        ch = TelegramChannel(bot_token="fake:token")
        assert ch.channel_id() == "telegram"

    def test_capabilities(self):
        ch = TelegramChannel(bot_token="fake:token")
        caps = ch.capabilities()
        assert "image" in caps["media"]
        assert caps["commands"] is True

    def test_bot_not_started_raises(self):
        ch = TelegramChannel(bot_token="fake:token")
        with pytest.raises(RuntimeError, match="not started"):
            _ = ch.bot

    def test_normalize_target_numeric(self):
        ch = TelegramChannel(bot_token="fake:token")
        assert ch.normalize_target("12345") == "12345"
        assert ch.normalize_target("-100123") == "-100123"

    def test_normalize_target_username(self):
        ch = TelegramChannel(bot_token="fake:token")
        assert ch.normalize_target("@mygroup") == "@mygroup"

    def test_normalize_target_invalid(self):
        ch = TelegramChannel(bot_token="fake:token")
        assert ch.normalize_target("invalid") is None


class TestTelegramChannelSend:
    async def test_send_text(self):
        ch = TelegramChannel(bot_token="fake:token")
        bot = AsyncMock()
        sent_msg = MagicMock()
        sent_msg.message_id = 42
        bot.send_message.return_value = sent_msg
        ch._bot = bot

        result = await ch.send_text("123", "Hello world")
        assert result.success is True
        assert result.channel == "telegram"

    async def test_send_media(self):
        ch = TelegramChannel(bot_token="fake:token")
        bot = AsyncMock()
        sent_msg = MagicMock()
        sent_msg.message_id = 43
        bot.send_photo.return_value = sent_msg
        ch._bot = bot

        result = await ch.send_media("123", "caption", "https://example.com/img.jpg")
        assert result.success is True


class TestTelegramChannelDownload:
    async def test_download_file(self):
        ch = TelegramChannel(bot_token="fake:token")
        bot = AsyncMock()
        tg_file = AsyncMock()
        tg_file.file_path = "photos/file_0.jpg"
        tg_file.download_as_bytearray.return_value = bytearray(b"image_data")
        bot.get_file.return_value = tg_file
        ch._bot = bot

        data, mime = await ch.download_file("file_id_123")
        assert data == b"image_data"
        assert mime == "image/jpeg"

    async def test_download_file_unknown_ext(self):
        ch = TelegramChannel(bot_token="fake:token")
        bot = AsyncMock()
        tg_file = AsyncMock()
        tg_file.file_path = "documents/file_0.xyz"
        tg_file.download_as_bytearray.return_value = bytearray(b"data")
        bot.get_file.return_value = tg_file
        ch._bot = bot

        data, mime = await ch.download_file("file_id_456")
        assert mime == "application/octet-stream"


class TestTelegramChannelHealthCheck:
    async def test_healthy(self):
        ch = TelegramChannel(bot_token="fake:token")
        bot = AsyncMock()
        me = MagicMock()
        me.username = "testbot"
        bot.get_me.return_value = me
        ch._bot = bot

        result = await ch.health_check()
        assert result["status"] == "healthy"
        assert result["bot_username"] == "testbot"

    async def test_unhealthy(self):
        ch = TelegramChannel(bot_token="fake:token")
        bot = AsyncMock()
        bot.get_me.side_effect = Exception("Connection refused")
        ch._bot = bot

        result = await ch.health_check()
        assert result["status"] == "unhealthy"
        assert "Connection refused" in result["error"]


class TestTelegramChannelHandleUpdate:
    async def test_dispatches_message(self):
        on_message = AsyncMock()
        ch = TelegramChannel(bot_token="fake:token", on_message=on_message)
        ch._bot = MagicMock()
        ch._bot_username = "testbot"

        # Create a mock update
        user = MagicMock()
        user.first_name = "Mario"
        user.last_name = "Rossi"
        user.username = "mario"
        user.id = 123

        message = MagicMock()
        message.text = "ciao"
        message.caption = None
        message.from_user = user
        message.chat_id = 42
        message.chat = MagicMock()
        message.chat.type = "private"
        message.message_id = 100
        message.photo = []
        message.voice = None
        message.audio = None
        message.video = None
        message.video_note = None
        message.document = None
        message.sticker = None
        message.reply_to_message = None
        message.message_thread_id = None
        message.media_group_id = None
        message.entities = []
        message.caption_entities = []

        update = MagicMock()
        update.update_id = 1
        update.message = message

        await ch._handle_update(update, None)
        on_message.assert_called_once()

    async def test_skips_group_without_mention(self):
        on_message = AsyncMock()
        ch = TelegramChannel(bot_token="fake:token", on_message=on_message)
        ch._bot = MagicMock()
        ch._bot_username = "testbot"

        user = MagicMock()
        user.first_name = "Mario"
        user.last_name = ""
        user.username = "mario"
        user.id = 123

        message = MagicMock()
        message.text = "just chatting"
        message.caption = None
        message.from_user = user
        message.chat_id = 42
        message.chat = MagicMock()
        message.chat.type = "supergroup"
        message.message_id = 100
        message.photo = []
        message.voice = None
        message.audio = None
        message.video = None
        message.video_note = None
        message.document = None
        message.sticker = None
        message.reply_to_message = None
        message.message_thread_id = None
        message.media_group_id = None
        message.entities = []
        message.caption_entities = []

        update = MagicMock()
        update.update_id = 1
        update.message = message

        await ch._handle_update(update, None)
        on_message.assert_not_called()

    async def test_command_dispatched(self):
        on_command = AsyncMock()
        ch = TelegramChannel(
            bot_token="fake:token",
            on_command=on_command,
        )
        ch._bot = MagicMock()
        ch._bot_username = "testbot"

        user = MagicMock()
        user.first_name = "Mario"
        user.last_name = ""
        user.username = "mario"
        user.id = 123

        message = MagicMock()
        message.text = "/help"
        message.caption = None
        message.from_user = user
        message.chat_id = 42
        message.chat = MagicMock()
        message.chat.type = "private"
        message.message_id = 100
        message.photo = []
        message.voice = None
        message.audio = None
        message.video = None
        message.video_note = None
        message.document = None
        message.sticker = None
        message.reply_to_message = None
        message.message_thread_id = None
        message.media_group_id = None
        message.entities = []
        message.caption_entities = []

        update = MagicMock()
        update.update_id = 1
        update.message = message

        await ch._handle_update(update, None)
        on_command.assert_called_once()
        assert on_command.call_args[0][1] == "help"


class TestProcessWebhookUpdate:
    async def test_processes_update(self):
        ch = TelegramChannel(bot_token="fake:token")
        ch._bot = MagicMock()
        app = AsyncMock()
        ch._app = app

        with patch("digital_brain.channels.telegram.plugin.Update") as mock_update_cls:
            mock_update = MagicMock()
            mock_update_cls.de_json.return_value = mock_update

            await ch.process_webhook_update({"update_id": 1})
            app.process_update.assert_called_once_with(mock_update)

    async def test_no_app_logs_warning(self):
        ch = TelegramChannel(bot_token="fake:token")
        ch._app = None
        # Should not raise
        await ch.process_webhook_update({"update_id": 1})


class TestGuessMimeType:
    def test_jpeg(self):
        assert _guess_mime_type("photos/file_0.jpg") == "image/jpeg"
        assert _guess_mime_type("file.jpeg") == "image/jpeg"

    def test_png(self):
        assert _guess_mime_type("file.png") == "image/png"

    def test_gif(self):
        assert _guess_mime_type("file.gif") == "image/gif"

    def test_ogg(self):
        assert _guess_mime_type("voice.ogg") == "audio/ogg"

    def test_mp4(self):
        assert _guess_mime_type("video.mp4") == "video/mp4"

    def test_pdf(self):
        assert _guess_mime_type("doc.pdf") == "application/pdf"

    def test_unknown(self):
        assert _guess_mime_type("file.xyz") == "application/octet-stream"

    def test_empty(self):
        assert _guess_mime_type("") == "application/octet-stream"
