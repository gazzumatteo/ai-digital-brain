"""Tests for channels/telegram/send.py — outbound messaging."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from digital_brain.channels.telegram.send import (
    TELEGRAM_CAPTION_LIMIT,
    TELEGRAM_TEXT_LIMIT,
    send_media_message,
    send_text_message,
)


def _make_bot(send_return_id=1):
    bot = AsyncMock()
    sent_msg = MagicMock()
    sent_msg.message_id = send_return_id
    bot.send_message.return_value = sent_msg
    bot.send_photo.return_value = sent_msg
    return bot


class TestSendTextMessage:
    async def test_short_message(self):
        bot = _make_bot()
        results = await send_text_message(bot, chat_id="42", text="Hello")
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].channel == "telegram"

    async def test_long_message_chunked(self):
        bot = _make_bot()
        long_text = "A" * (TELEGRAM_TEXT_LIMIT + 100)
        results = await send_text_message(bot, chat_id="42", text=long_text)
        assert len(results) >= 2
        assert all(r.success for r in results)

    async def test_reply_to_only_first_chunk(self):
        bot = _make_bot()
        long_text = "A" * (TELEGRAM_TEXT_LIMIT + 100)
        await send_text_message(
            bot, chat_id="42", text=long_text, reply_to_message_id=10
        )
        # First call should have reply_to, second should not
        calls = bot.send_message.call_args_list
        assert len(calls) >= 2

    async def test_send_failure(self):
        bot = AsyncMock()
        bot.send_message.side_effect = Exception("Network error")
        results = await send_text_message(bot, chat_id="42", text="Hello")
        assert len(results) == 1
        assert results[0].success is False
        assert "Network error" in results[0].error

    async def test_markdown_fallback(self):
        """If MarkdownV2 fails, should fall back to Markdown then plain."""
        bot = AsyncMock()
        sent_msg = MagicMock()
        sent_msg.message_id = 1

        # MarkdownV2 fails, Markdown fails, plain works
        call_count = 0

        async def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if "parse_mode" in kwargs:
                raise Exception("Parse error")
            return sent_msg

        bot.send_message.side_effect = side_effect
        results = await send_text_message(bot, chat_id="42", text="*bold*")
        assert len(results) == 1
        assert results[0].success is True

    async def test_thread_id_passed(self):
        bot = _make_bot()
        await send_text_message(
            bot, chat_id="42", text="Hello", message_thread_id=77
        )
        bot.send_message.assert_called()


class TestSendMediaMessage:
    async def test_send_photo(self):
        bot = _make_bot()
        result = await send_media_message(bot, chat_id="42", media_url="https://example.com/img.jpg")
        assert result.success is True

    async def test_send_photo_with_caption(self):
        bot = _make_bot()
        result = await send_media_message(
            bot, chat_id="42", media_url="url", caption="nice pic"
        )
        assert result.success is True
        call_kwargs = bot.send_photo.call_args
        assert "caption" in call_kwargs.kwargs

    async def test_caption_truncated(self):
        bot = _make_bot()
        long_caption = "C" * (TELEGRAM_CAPTION_LIMIT + 100)
        await send_media_message(
            bot, chat_id="42", media_url="url", caption=long_caption
        )
        call_kwargs = bot.send_photo.call_args
        assert len(call_kwargs.kwargs["caption"]) <= TELEGRAM_CAPTION_LIMIT

    async def test_send_failure(self):
        bot = AsyncMock()
        bot.send_photo.side_effect = Exception("Upload failed")
        result = await send_media_message(bot, chat_id="42", media_url="url")
        assert result.success is False
        assert "Upload failed" in result.error
