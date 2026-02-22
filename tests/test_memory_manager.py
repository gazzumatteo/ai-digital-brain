"""Tests for MemoryManager."""

from digital_brain.memory.manager import MemoryManager


class TestMemoryManagerAdd:
    def test_add_string(self, memory_manager: MemoryManager, mock_mem0):
        result = memory_manager.add("User likes pizza", user_id="alice")
        mock_mem0.add.assert_called_once()
        call_args = mock_mem0.add.call_args
        assert call_args[0][0] == [{"role": "user", "content": "User likes pizza"}]
        assert call_args[1]["user_id"] == "alice"
        assert "results" in result

    def test_add_messages_list(self, memory_manager: MemoryManager, mock_mem0):
        msgs = [{"role": "user", "content": "I love sushi"}]
        memory_manager.add(msgs, user_id="bob")
        mock_mem0.add.assert_called_once_with(msgs, user_id="bob", metadata=None, infer=True)

    def test_add_with_metadata(self, memory_manager: MemoryManager, mock_mem0):
        memory_manager.add("Fact", user_id="alice", metadata={"category": "food"})
        call_args = mock_mem0.add.call_args
        assert call_args[1]["metadata"] == {"category": "food"}


class TestMemoryManagerSearch:
    def test_search_returns_results(self, memory_manager: MemoryManager):
        result = memory_manager.search("food preferences", user_id="alice")
        assert result.total == 2
        assert result.results[0].memory == "User likes Italian food"
        assert result.results[0].score == 0.95

    def test_search_empty(self, memory_manager: MemoryManager, mock_mem0):
        mock_mem0.search.return_value = {"results": []}
        result = memory_manager.search("unknown topic", user_id="alice")
        assert result.total == 0
        assert result.results == []


class TestMemoryManagerGetAll:
    def test_get_all(self, memory_manager: MemoryManager):
        result = memory_manager.get_all(user_id="alice")
        assert result.total == 3
        assert result.results[2].memory == "User works at Acme Corp"


class TestMemoryManagerDelete:
    def test_delete(self, memory_manager: MemoryManager, mock_mem0):
        memory_manager.delete("mem_1")
        mock_mem0.delete.assert_called_once_with(memory_id="mem_1")

    def test_delete_all(self, memory_manager: MemoryManager, mock_mem0):
        memory_manager.delete_all("alice")
        mock_mem0.delete_all.assert_called_once_with(user_id="alice")
