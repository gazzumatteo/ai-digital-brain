"""Tests for middleware (correlation IDs, rate limiting)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from digital_brain.middleware import CorrelationIDMiddleware, RateLimitMiddleware


@pytest.fixture()
def simple_app():
    """Minimal FastAPI app for middleware testing."""
    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"pong": True}

    return app


class TestCorrelationIDMiddleware:
    def test_generates_correlation_id(self, simple_app):
        simple_app.add_middleware(CorrelationIDMiddleware)
        client = TestClient(simple_app)
        resp = client.get("/ping")
        assert resp.status_code == 200
        assert "X-Correlation-ID" in resp.headers
        assert len(resp.headers["X-Correlation-ID"]) == 12

    def test_echoes_provided_correlation_id(self, simple_app):
        simple_app.add_middleware(CorrelationIDMiddleware)
        client = TestClient(simple_app)
        resp = client.get("/ping", headers={"X-Correlation-ID": "my-custom-id"})
        assert resp.headers["X-Correlation-ID"] == "my-custom-id"


class TestRateLimitMiddleware:
    def test_allows_requests_under_limit(self, simple_app):
        simple_app.add_middleware(RateLimitMiddleware, requests_per_minute=10)
        client = TestClient(simple_app)
        for _ in range(10):
            resp = client.get("/ping")
            assert resp.status_code == 200

    def test_blocks_requests_over_limit(self, simple_app):
        simple_app.add_middleware(RateLimitMiddleware, requests_per_minute=3)
        client = TestClient(simple_app)
        for _ in range(3):
            resp = client.get("/ping")
            assert resp.status_code == 200
        resp = client.get("/ping")
        assert resp.status_code == 429
        assert "Rate limit" in resp.json()["detail"]
        assert resp.headers["Retry-After"] == "60"
