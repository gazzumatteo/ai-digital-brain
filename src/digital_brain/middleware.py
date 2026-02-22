"""FastAPI middleware: correlation IDs, request logging, and rate limiting."""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from digital_brain.config import get_settings
from digital_brain.logging_config import correlation_id_var, generate_correlation_id
from digital_brain.metrics import metrics

logger = logging.getLogger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Attach a correlation ID to every request and log request/response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        cid = request.headers.get("X-Correlation-ID") or generate_correlation_id()
        correlation_id_var.set(cid)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Correlation-ID"] = cid

        metrics.record_time("http_request", elapsed_ms)
        metrics.inc(f"http_{response.status_code}")

        logger.info(
            "%s %s -> %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            extra={
                "operation": "http_request",
                "duration_ms": round(elapsed_ms, 1),
            },
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding-window rate limiter keyed by client IP."""

    def __init__(self, app, requests_per_minute: int = 60) -> None:  # noqa: N803
        super().__init__(app)
        self._limit = requests_per_minute
        self._window: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - 60

        # Prune old entries
        timestamps = self._window[client_ip]
        self._window[client_ip] = [t for t in timestamps if t > window_start]

        if len(self._window[client_ip]) >= self._limit:
            metrics.inc("rate_limited")
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": "60"},
            )

        self._window[client_ip].append(now)
        return await call_next(request)


def register_middleware(app) -> None:  # noqa: ANN001
    """Register all middleware on the FastAPI app."""
    settings = get_settings()

    # Order matters: outermost middleware runs first
    app.add_middleware(CorrelationIDMiddleware)

    if settings.rate_limit.enabled:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=settings.rate_limit.requests_per_minute,
        )
