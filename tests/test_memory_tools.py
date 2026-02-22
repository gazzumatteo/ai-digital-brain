"""Tests for ADK memory tool functions."""

from digital_brain.memory.manager import MemoryManager
from digital_brain.memory.tools import (
    memory_delete,
    memory_get_all,
    memory_search,
    memory_store,
    set_memory_manager,
)


class TestMemoryTools:
    def setup_method(self, method):
        """Reset the global manager before each test."""
        set_memory_manager(None)

    def test_memory_store(self, memory_manager: MemoryManager):
        set_memory_manager(memory_manager)
        result = memory_store("User likes sushi", user_id="alice")
        assert result["status"] == "saved"

    def test_memory_store_with_category(self, memory_manager: MemoryManager):
        set_memory_manager(memory_manager)
        result = memory_store("User likes sushi", user_id="alice", category="food")
        assert result["status"] == "saved"

    def test_memory_search_found(self, memory_manager: MemoryManager):
        set_memory_manager(memory_manager)
        result = memory_search("food", user_id="alice")
        assert result["status"] == "found"
        assert result["count"] == 2
        assert "Italian food" in result["memories"]

    def test_memory_search_empty(self, memory_manager: MemoryManager, mock_mem0):
        set_memory_manager(memory_manager)
        mock_mem0.search.return_value = {"results": []}
        result = memory_search("unknown", user_id="alice")
        assert result["status"] == "no_memories"

    def test_memory_get_all(self, memory_manager: MemoryManager):
        set_memory_manager(memory_manager)
        result = memory_get_all(user_id="alice")
        assert result["status"] == "found"
        assert result["count"] == 3

    def test_memory_delete(self, memory_manager: MemoryManager):
        set_memory_manager(memory_manager)
        result = memory_delete(memory_id="mem_1")
        assert result["status"] == "deleted"
        assert result["memory_id"] == "mem_1"
