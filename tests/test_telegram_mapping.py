"""Tests for channels/telegram/mapping.py — TelegramUserMapper."""

from __future__ import annotations

from digital_brain.channels.telegram.mapping import TelegramUserMapper


class TestTelegramUserMapper:
    def test_resolve_creates_mapping(self):
        mapper = TelegramUserMapper()
        brain_id = mapper.resolve(12345, "Mario")
        assert brain_id == "tg_12345"

    def test_resolve_returns_existing(self):
        mapper = TelegramUserMapper()
        first = mapper.resolve(12345)
        second = mapper.resolve(12345)
        assert first == second

    def test_resolve_string_id(self):
        mapper = TelegramUserMapper()
        brain_id = mapper.resolve("12345")
        assert brain_id == "tg_12345"

    def test_get_brain_id(self):
        mapper = TelegramUserMapper()
        assert mapper.get_brain_id(999) is None
        mapper.resolve(999)
        assert mapper.get_brain_id(999) == "tg_999"

    def test_display_name(self):
        mapper = TelegramUserMapper()
        mapper.resolve(100, "Alice")
        assert mapper.get_display_name("tg_100") == "Alice"

    def test_set_display_name(self):
        mapper = TelegramUserMapper()
        mapper.resolve(100)
        mapper.set_display_name("tg_100", "Bob")
        assert mapper.get_display_name("tg_100") == "Bob"

    def test_display_name_unknown(self):
        mapper = TelegramUserMapper()
        assert mapper.get_display_name("tg_999") is None

    def test_multiple_users(self):
        mapper = TelegramUserMapper()
        a = mapper.resolve(1, "Alice")
        b = mapper.resolve(2, "Bob")
        assert a != b
        assert mapper.get_display_name(a) == "Alice"
        assert mapper.get_display_name(b) == "Bob"
