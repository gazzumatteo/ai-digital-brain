"""Tests for channels/telegram/handlers.py — message normalization and utilities."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from digital_brain.channels.telegram.handlers import (
    MediaGroupBuffer,
    extract_media_attachment,
    extract_sender_name,
    is_bot_mentioned,
    is_command,
    normalize_update,
    parse_command,
)


def _make_user(first="John", last="Doe", username="johndoe", user_id=123):
    user = MagicMock()
    user.first_name = first
    user.last_name = last
    user.username = username
    user.id = user_id
    return user


def _make_message(
    text="hello",
    user=None,
    chat_id=42,
    chat_type="private",
    message_id=100,
    photo=None,
    voice=None,
    audio=None,
    video=None,
    video_note=None,
    document=None,
    sticker=None,
    caption=None,
    reply_to_message=None,
    message_thread_id=None,
    media_group_id=None,
    entities=None,
    caption_entities=None,
):
    msg = MagicMock()
    msg.text = text
    msg.caption = caption
    msg.from_user = user or _make_user()
    msg.chat_id = chat_id
    msg.chat = MagicMock()
    msg.chat.type = chat_type
    msg.message_id = message_id
    msg.photo = photo or []
    msg.voice = voice
    msg.audio = audio
    msg.video = video
    msg.video_note = video_note
    msg.document = document
    msg.sticker = sticker
    msg.reply_to_message = reply_to_message
    msg.message_thread_id = message_thread_id
    msg.media_group_id = media_group_id
    msg.entities = entities or []
    msg.caption_entities = caption_entities or []
    return msg


def _make_update(message=None, update_id=1):
    update = MagicMock()
    update.update_id = update_id
    update.message = message
    return update


class TestExtractSenderName:
    def test_full_name(self):
        msg = _make_message(user=_make_user(first="Mario", last="Rossi"))
        assert extract_sender_name(msg) == "Mario Rossi"

    def test_first_name_only(self):
        msg = _make_message(user=_make_user(first="Mario", last=""))
        assert extract_sender_name(msg) == "Mario"

    def test_username_fallback(self):
        msg = _make_message(user=_make_user(first="", last="", username="mario_r"))
        assert extract_sender_name(msg) == "mario_r"

    def test_id_fallback(self):
        msg = _make_message(user=_make_user(first="", last="", username="", user_id=999))
        assert extract_sender_name(msg) == "999"

    def test_no_user(self):
        msg = _make_message()
        msg.from_user = None
        assert extract_sender_name(msg) == "Unknown"


class TestExtractMediaAttachment:
    def test_photo(self):
        photo = MagicMock()
        photo.file_id = "photo_id"
        photo.file_size = 5000
        photo.width = 800
        photo.height = 600
        msg = _make_message(photo=[MagicMock(), photo], caption="my photo")
        att = extract_media_attachment(msg)
        assert att is not None
        assert att.type == "image"
        assert att.file_id == "photo_id"
        assert att.width == 800
        assert att.caption == "my photo"

    def test_voice(self):
        voice = MagicMock()
        voice.file_id = "voice_id"
        voice.file_size = 1000
        voice.mime_type = "audio/ogg"
        voice.duration = 5
        msg = _make_message(voice=voice, text=None)
        att = extract_media_attachment(msg)
        assert att is not None
        assert att.type == "voice"
        assert att.duration_seconds == 5.0

    def test_audio(self):
        audio = MagicMock()
        audio.file_id = "audio_id"
        audio.file_size = 2000
        audio.mime_type = "audio/mpeg"
        audio.duration = 180
        audio.file_name = "song.mp3"
        msg = _make_message(audio=audio, text=None)
        att = extract_media_attachment(msg)
        assert att is not None
        assert att.type == "audio"
        assert att.filename == "song.mp3"

    def test_video(self):
        video = MagicMock()
        video.file_id = "video_id"
        video.file_size = 10000
        video.mime_type = "video/mp4"
        video.duration = 30
        video.width = 1920
        video.height = 1080
        msg = _make_message(video=video, text=None)
        att = extract_media_attachment(msg)
        assert att is not None
        assert att.type == "video"
        assert att.width == 1920

    def test_video_note(self):
        vn = MagicMock()
        vn.file_id = "vn_id"
        vn.file_size = 3000
        vn.duration = 10
        vn.length = 240
        msg = _make_message(video_note=vn, text=None)
        att = extract_media_attachment(msg)
        assert att is not None
        assert att.type == "video"
        assert att.width == 240
        assert att.height == 240

    def test_document(self):
        doc = MagicMock()
        doc.file_id = "doc_id"
        doc.file_size = 50000
        doc.mime_type = "application/pdf"
        doc.file_name = "report.pdf"
        msg = _make_message(document=doc, text=None)
        att = extract_media_attachment(msg)
        assert att is not None
        assert att.type == "document"
        assert att.filename == "report.pdf"

    def test_sticker(self):
        stk = MagicMock()
        stk.file_id = "stk_id"
        stk.file_size = 8000
        stk.width = 512
        stk.height = 512
        stk.emoji = "\U0001f600"
        msg = _make_message(sticker=stk, text=None)
        att = extract_media_attachment(msg)
        assert att is not None
        assert att.type == "sticker"
        assert att.caption == "\U0001f600"

    def test_no_media(self):
        msg = _make_message(text="just text")
        att = extract_media_attachment(msg)
        assert att is None


class TestNormalizeUpdate:
    def test_text_message(self):
        msg = _make_message(text="ciao", chat_id=42, chat_type="private")
        update = _make_update(message=msg, update_id=10)
        result = normalize_update(update)
        assert result is not None
        assert result.channel == "telegram"
        assert result.chat_id == "42"
        assert result.text == "ciao"
        assert result.raw["update_id"] == 10
        assert result.raw["is_group"] is False

    def test_group_message(self):
        msg = _make_message(chat_type="supergroup")
        update = _make_update(message=msg)
        result = normalize_update(update)
        assert result is not None
        assert result.raw["is_group"] is True

    def test_no_message(self):
        update = _make_update(message=None)
        assert normalize_update(update) is None

    def test_service_message(self):
        msg = _make_message()
        msg.from_user = None
        update = _make_update(message=msg)
        assert normalize_update(update) is None

    def test_reply_to_message(self):
        reply = MagicMock()
        reply.message_id = 50
        msg = _make_message(reply_to_message=reply)
        update = _make_update(message=msg)
        result = normalize_update(update)
        assert result is not None
        assert result.reply_to_id == "50"

    def test_thread_id(self):
        msg = _make_message(message_thread_id=77)
        update = _make_update(message=msg)
        result = normalize_update(update)
        assert result is not None
        assert result.thread_id == "77"

    def test_media_group_id(self):
        msg = _make_message(media_group_id="mg123")
        update = _make_update(message=msg)
        result = normalize_update(update)
        assert result is not None
        assert result.raw["media_group_id"] == "mg123"

    def test_caption_as_text(self):
        msg = _make_message(text=None, caption="photo caption")
        update = _make_update(message=msg)
        result = normalize_update(update)
        assert result is not None
        assert result.text == "photo caption"


class TestIsBotMentioned:
    def test_at_mention_in_text(self):
        msg = _make_message(text="Hey @mybot what's up")
        assert is_bot_mentioned(msg, "mybot") is True

    def test_no_mention(self):
        msg = _make_message(text="Hello everyone")
        assert is_bot_mentioned(msg, "mybot") is False

    def test_mention_entity(self):
        entity = MagicMock()
        entity.type = "mention"
        entity.offset = 0
        entity.length = 6
        msg = _make_message(text="@mybot hello", entities=[entity])
        assert is_bot_mentioned(msg, "mybot") is True

    def test_reply_to_bot(self):
        reply_msg = MagicMock()
        reply_msg.from_user = MagicMock()
        reply_msg.from_user.username = "mybot"
        msg = _make_message(text="yes", reply_to_message=reply_msg)
        assert is_bot_mentioned(msg, "mybot") is True

    def test_empty_bot_username(self):
        msg = _make_message(text="@mybot hello")
        assert is_bot_mentioned(msg, "") is False


class TestIsCommand:
    def test_command(self):
        assert is_command("/start") is True
        assert is_command("/help more") is True

    def test_not_command(self):
        assert is_command("hello") is False
        assert is_command("") is False


class TestParseCommand:
    def test_simple_command(self):
        assert parse_command("/start") == ("start", "")

    def test_command_with_args(self):
        assert parse_command("/forget all") == ("forget", "all")

    def test_command_with_bot_suffix(self):
        assert parse_command("/help@mybot") == ("help", "")

    def test_not_a_command(self):
        assert parse_command("hello") == ("", "hello")

    def test_empty(self):
        assert parse_command("") == ("", "")


class TestMediaGroupBuffer:
    async def test_buffers_and_flushes(self):
        from digital_brain.channels.base import InboundMessage, MediaAttachment

        flushed: list[InboundMessage] = []

        async def on_flush(msg: InboundMessage) -> None:
            flushed.append(msg)

        buffer = MediaGroupBuffer(timeout_ms=50)
        buffer.set_flush_callback(on_flush)

        msg1 = InboundMessage(
            channel="telegram",
            chat_id="42",
            sender_id="1",
            sender_name="Test",
            text="",
            media=[MediaAttachment(type="image", mime_type="image/jpeg", file_id="f1")],
            raw={"message_id": 1},
        )
        msg2 = InboundMessage(
            channel="telegram",
            chat_id="42",
            sender_id="1",
            sender_name="Test",
            text="",
            media=[MediaAttachment(type="image", mime_type="image/jpeg", file_id="f2")],
            raw={"message_id": 2},
        )

        await buffer.add("mg1", msg1)
        await buffer.add("mg1", msg2)

        # Wait for flush
        await asyncio.sleep(0.1)
        assert len(flushed) == 1
        assert len(flushed[0].media) == 2

    async def test_different_groups_separate(self):
        from digital_brain.channels.base import InboundMessage, MediaAttachment

        flushed: list[InboundMessage] = []

        async def on_flush(msg: InboundMessage) -> None:
            flushed.append(msg)

        buffer = MediaGroupBuffer(timeout_ms=50)
        buffer.set_flush_callback(on_flush)

        msg1 = InboundMessage(
            channel="telegram",
            chat_id="42",
            sender_id="1",
            sender_name="Test",
            text="album1",
            media=[MediaAttachment(type="image", mime_type="image/jpeg", file_id="f1")],
            raw={"message_id": 1},
        )
        msg2 = InboundMessage(
            channel="telegram",
            chat_id="42",
            sender_id="1",
            sender_name="Test",
            text="album2",
            media=[MediaAttachment(type="image", mime_type="image/jpeg", file_id="f2")],
            raw={"message_id": 2},
        )

        await buffer.add("mg1", msg1)
        await buffer.add("mg2", msg2)

        await asyncio.sleep(0.1)
        assert len(flushed) == 2
