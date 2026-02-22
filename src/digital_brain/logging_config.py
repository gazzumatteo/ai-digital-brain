"""Structured logging configuration with JSON output and sanitization."""

from __future__ import annotations

import json
import logging
import re
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# Context variable for per-request correlation ID
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

# Patterns that look like secrets / API keys / tokens
_SENSITIVE_PATTERNS = [
    re.compile(r"(AIza[0-9A-Za-z_-]{35})", re.ASCII),  # Google API key
    re.compile(r"(sk-[A-Za-z0-9]{20,})", re.ASCII),  # OpenAI key
    re.compile(r"(ghp_[A-Za-z0-9]{36,})", re.ASCII),  # GitHub PAT
    re.compile(r"(password\s*[=:]\s*)\S+", re.IGNORECASE),
    re.compile(r"(secret\s*[=:]\s*)\S+", re.IGNORECASE),
    re.compile(r"(token\s*[=:]\s*)\S+", re.IGNORECASE),
    re.compile(r"(api[_-]?key\s*[=:]\s*)\S+", re.IGNORECASE),
]


def generate_correlation_id() -> str:
    """Generate a short correlation ID for request tracing."""
    return uuid.uuid4().hex[:12]


def sanitize(value: str) -> str:
    """Redact known secret patterns from a string."""
    for pattern in _SENSITIVE_PATTERNS:
        value = pattern.sub(lambda m: m.group(0)[:4] + "***REDACTED***", value)
    return value


class JSONFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": sanitize(record.getMessage()),
        }

        cid = correlation_id_var.get("")
        if cid:
            entry["correlation_id"] = cid

        if record.exc_info and record.exc_info[1]:
            entry["exception"] = sanitize(self.formatException(record.exc_info))

        # Merge any extra fields attached to the record
        for key in ("user_id", "session_id", "operation", "duration_ms", "memory_count"):
            val = getattr(record, key, None)
            if val is not None:
                entry[key] = val

        return json.dumps(entry, default=str)


class SanitizedTextFormatter(logging.Formatter):
    """Standard text formatter that still redacts secrets."""

    def format(self, record: logging.LogRecord) -> str:
        cid = correlation_id_var.get("")
        prefix = f"[{cid}] " if cid else ""
        record.msg = sanitize(str(record.msg))
        base = super().format(record)
        return f"{prefix}{base}"


def setup_logging(level: str = "INFO", fmt: str = "json") -> None:
    """Configure root logger with the chosen format."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    root.handlers.clear()

    handler = logging.StreamHandler()
    if fmt == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            SanitizedTextFormatter("%(asctime)s %(levelname)-8s %(name)s — %(message)s")
        )
    root.addHandler(handler)

    # Quieten noisy third-party loggers
    for name in ("httpx", "httpcore", "urllib3", "google", "grpc"):
        logging.getLogger(name).setLevel(logging.WARNING)
