"""Tests for the context signals tool."""

from unittest.mock import patch

from digital_brain.memory.schemas import MemorySearchResult
from digital_brain.tools.context_tool import get_context_signals


class TestContextSignals:
    def test_returns_expected_keys(self):
        with patch("digital_brain.tools.context_tool._get_manager") as mock_mgr:
            mock_mgr.return_value.get_recent.return_value = MemorySearchResult(results=[], total=0)
            result = get_context_signals(user_id="alice")

        assert "time_of_day" in result
        assert "day_of_week" in result
        assert "is_weekend" in result
        assert "recent_topics" in result
        assert result["time_of_day"] in ("morning", "afternoon", "evening")

    def test_handles_manager_error(self):
        with patch("digital_brain.tools.context_tool._get_manager") as mock_mgr:
            mock_mgr.return_value.get_recent.side_effect = RuntimeError("no connection")
            result = get_context_signals(user_id="alice")

        assert result["recent_topics"] == []
        assert result["recent_topic_count"] == 0
