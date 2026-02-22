"""Tests for api/webhooks.py — webhook endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from digital_brain.api.webhooks import create_webhook_router


def _make_app(channel=None, webhook_secret: str = "") -> FastAPI:
    app = FastAPI()
    router = create_webhook_router(
        get_telegram_channel=lambda: channel,
        webhook_secret=webhook_secret,
    )
    app.include_router(router)
    return app


class TestTelegramWebhook:
    def test_no_channel_returns_503(self):
        app = _make_app(channel=None)
        client = TestClient(app)
        resp = client.post("/webhooks/telegram", json={"update_id": 1})
        assert resp.status_code == 503

    def test_valid_update_processed(self):
        channel = MagicMock()
        channel.process_webhook_update = AsyncMock()
        app = _make_app(channel=channel)
        client = TestClient(app)
        resp = client.post("/webhooks/telegram", json={"update_id": 1})
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        channel.process_webhook_update.assert_called_once_with({"update_id": 1})

    def test_secret_required_but_missing(self):
        channel = MagicMock()
        app = _make_app(channel=channel, webhook_secret="mysecret")
        client = TestClient(app)
        resp = client.post("/webhooks/telegram", json={"update_id": 1})
        assert resp.status_code == 403

    def test_secret_required_and_valid(self):
        channel = MagicMock()
        channel.process_webhook_update = AsyncMock()
        app = _make_app(channel=channel, webhook_secret="mysecret")
        client = TestClient(app)
        resp = client.post(
            "/webhooks/telegram",
            json={"update_id": 1},
            headers={"X-Telegram-Bot-Api-Secret-Token": "mysecret"},
        )
        assert resp.status_code == 200

    def test_secret_required_but_wrong(self):
        channel = MagicMock()
        app = _make_app(channel=channel, webhook_secret="mysecret")
        client = TestClient(app)
        resp = client.post(
            "/webhooks/telegram",
            json={"update_id": 1},
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrongsecret"},
        )
        assert resp.status_code == 403

    def test_processing_error_returns_500(self):
        channel = MagicMock()
        channel.process_webhook_update = AsyncMock(
            side_effect=RuntimeError("boom")
        )
        app = _make_app(channel=channel)
        client = TestClient(app)
        resp = client.post("/webhooks/telegram", json={"update_id": 1})
        assert resp.status_code == 500
