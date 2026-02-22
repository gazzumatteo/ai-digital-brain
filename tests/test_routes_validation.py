"""Tests for route-level input validation and user scoping."""

from __future__ import annotations

import pytest

from digital_brain.api.routes import ChatRequest, _validate_user_id


class TestUserIDValidation:
    def test_valid_user_ids(self):
        for uid in ("alice", "user-1", "user_2", "ABC123", "a"):
            assert _validate_user_id(uid) == uid

    def test_rejects_empty(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_user_id("")
        assert exc_info.value.status_code == 400

    def test_rejects_path_traversal(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            _validate_user_id("../etc/passwd")

    def test_rejects_special_characters(self):
        from fastapi import HTTPException

        for bad in ("user@evil", "user;drop", "a b c", "user/id", "<script>"):
            with pytest.raises(HTTPException):
                _validate_user_id(bad)

    def test_rejects_too_long(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            _validate_user_id("a" * 129)

    def test_max_length_is_ok(self):
        uid = "a" * 128
        assert _validate_user_id(uid) == uid


class TestChatRequestValidation:
    def test_valid_request(self):
        req = ChatRequest(user_id="alice", message="hello")
        assert req.user_id == "alice"
        assert req.message == "hello"

    def test_rejects_invalid_user_id(self):
        with pytest.raises(ValueError, match="user_id"):
            ChatRequest(user_id="user@evil", message="hello")

    def test_rejects_empty_message(self):
        with pytest.raises(ValueError, match="message"):
            ChatRequest(user_id="alice", message="   ")
