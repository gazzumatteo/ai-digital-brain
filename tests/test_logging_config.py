"""Tests for structured logging and sanitization."""

from __future__ import annotations

import json
import logging

from digital_brain.logging_config import (
    JSONFormatter,
    SanitizedTextFormatter,
    correlation_id_var,
    generate_correlation_id,
    sanitize,
    setup_logging,
)


class TestSanitize:
    def test_redacts_google_api_key(self):
        raw = "key=AIzaSyDs5eruHQGNK4hghqBKeC14J-eHSdEtR0w"
        result = sanitize(raw)
        assert "AIzaSyDs5eruHQGNK4hghqBKeC14J-eHSdEtR0w" not in result
        assert "REDACTED" in result

    def test_redacts_openai_key(self):
        raw = "token sk-abc123def456ghi789jkl012mno345pqrstu"
        result = sanitize(raw)
        assert "sk-abc123def456ghi789jkl012mno345pqrstu" not in result
        assert "REDACTED" in result

    def test_redacts_password_in_log(self):
        raw = "connecting with password=supersecret123"
        result = sanitize(raw)
        assert "supersecret123" not in result

    def test_leaves_normal_text_unchanged(self):
        raw = "User likes Italian food"
        assert sanitize(raw) == raw

    def test_redacts_github_pat(self):
        raw = "token ghp_abcdefghijklmnopqrstuvwxyz0123456789"
        result = sanitize(raw)
        assert "ghp_abcdefghijklmnopqrstuvwxyz0123456789" not in result
        assert "REDACTED" in result


class TestCorrelationID:
    def test_generate_returns_12_char_hex(self):
        cid = generate_correlation_id()
        assert len(cid) == 12
        int(cid, 16)  # should not raise

    def test_context_var_default_is_empty(self):
        assert correlation_id_var.get("") == ""

    def test_context_var_can_be_set(self):
        token = correlation_id_var.set("test-id-123")
        assert correlation_id_var.get() == "test-id-123"
        correlation_id_var.reset(token)


class TestJSONFormatter:
    def test_produces_valid_json(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "hello world"
        assert "timestamp" in parsed

    def test_includes_correlation_id_when_set(self):
        formatter = JSONFormatter()
        token = correlation_id_var.set("abc123")
        try:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="test message",
                args=(),
                exc_info=None,
            )
            output = formatter.format(record)
            parsed = json.loads(output)
            assert parsed["correlation_id"] == "abc123"
        finally:
            correlation_id_var.reset(token)

    def test_sanitizes_message(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="key=AIzaSyDs5eruHQGNK4hghqBKeC14J-eHSdEtR0w leaked",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "AIzaSyDs5eruHQGNK4hghqBKeC14J-eHSdEtR0w" not in parsed["message"]

    def test_includes_extra_fields(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        record.user_id = "alice"
        record.operation = "chat"
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["user_id"] == "alice"
        assert parsed["operation"] == "chat"


class TestSanitizedTextFormatter:
    def test_redacts_secrets_in_text_format(self):
        formatter = SanitizedTextFormatter("%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="api_key = sk-abc123def456ghi789jkl012mno345pqrstu",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        assert "sk-abc123def456ghi789jkl012mno345pqrstu" not in output


class TestSetupLogging:
    def test_json_format(self):
        setup_logging(level="DEBUG", fmt="json")
        root = logging.getLogger()
        assert root.level == logging.DEBUG
        assert any(isinstance(h.formatter, JSONFormatter) for h in root.handlers)

    def test_text_format(self):
        setup_logging(level="WARNING", fmt="text")
        root = logging.getLogger()
        assert root.level == logging.WARNING
        assert any(isinstance(h.formatter, SanitizedTextFormatter) for h in root.handlers)
