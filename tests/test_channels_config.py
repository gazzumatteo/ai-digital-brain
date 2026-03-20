"""Tests for channel-related configuration (TelegramSettings, MediaSettings)."""

from __future__ import annotations

from digital_brain.config import MediaSettings, Settings, TelegramSettings


class TestTelegramSettings:
    def test_defaults(self, monkeypatch):
        monkeypatch.delenv("TELEGRAM_ENABLED", raising=False)
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_WEBHOOK_URL", raising=False)
        monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
        monkeypatch.delenv("TELEGRAM_DM_POLICY", raising=False)
        monkeypatch.delenv("TELEGRAM_ALLOW_FROM", raising=False)
        monkeypatch.delenv("TELEGRAM_DEBOUNCE_MS", raising=False)
        s = TelegramSettings(_env_file=None)
        assert s.enabled is False
        assert s.bot_token == ""
        assert s.webhook_url == ""
        assert s.webhook_secret == ""
        assert s.dm_policy == "pairing"
        assert s.allow_from == []
        assert s.debounce_ms == 1500

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_ENABLED", "true")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
        monkeypatch.setenv("TELEGRAM_DM_POLICY", "open")
        s = TelegramSettings()
        assert s.enabled is True
        assert s.bot_token == "123:ABC"
        assert s.dm_policy == "open"


class TestMediaSettings:
    def test_defaults(self):
        s = MediaSettings()
        assert s.max_file_size_mb == 20
        assert "image/*" in s.allowed_types
        assert "application/pdf" in s.allowed_types

    def test_custom_size(self, monkeypatch):
        monkeypatch.setenv("MEDIA_MAX_FILE_SIZE_MB", "50")
        s = MediaSettings()
        assert s.max_file_size_mb == 50


class TestSettingsIntegration:
    def test_settings_includes_telegram(self, monkeypatch):
        monkeypatch.delenv("TELEGRAM_ENABLED", raising=False)
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_WEBHOOK_URL", raising=False)
        monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
        monkeypatch.delenv("TELEGRAM_DM_POLICY", raising=False)
        monkeypatch.delenv("TELEGRAM_ALLOW_FROM", raising=False)
        monkeypatch.delenv("TELEGRAM_DEBOUNCE_MS", raising=False)
        s = Settings(telegram=TelegramSettings(_env_file=None))
        assert isinstance(s.telegram, TelegramSettings)
        assert s.telegram.enabled is False

    def test_settings_includes_media(self):
        s = Settings()
        assert isinstance(s.media, MediaSettings)
        assert s.media.max_file_size_mb == 20
