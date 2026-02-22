"""Shared fixtures for Digital Brain tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from digital_brain.config import (
    EmbedderSettings,
    LLMSettings,
    LoggingSettings,
    MemorySettings,
    Neo4jSettings,
    QdrantSettings,
    RateLimitSettings,
    Settings,
)
from digital_brain.memory.manager import MemoryManager


@pytest.fixture()
def settings() -> Settings:
    """Return a Settings instance with test defaults."""
    return Settings(
        llm=LLMSettings(provider="gemini", model="gemini-3-flash-preview"),
        embedder=EmbedderSettings(provider="ollama", model="nomic-embed-text:latest", dims=768),
        qdrant=QdrantSettings(host="localhost", port=6333, collection="test_memories"),
        neo4j=Neo4jSettings(enabled=False),
        memory=MemorySettings(ttl_days=0),
        logging=LoggingSettings(level="DEBUG", format="text"),
        rate_limit=RateLimitSettings(enabled=False),
    )


@pytest.fixture()
def mock_mem0():
    """Patch Mem0 Memory.from_config to return a mock."""
    mock_memory = MagicMock()
    mock_memory.add.return_value = {"results": [{"id": "mem_1", "event": "ADD"}]}
    mock_memory.search.return_value = {
        "results": [
            {"id": "mem_1", "memory": "User likes Italian food", "score": 0.95},
            {"id": "mem_2", "memory": "User prefers morning meetings", "score": 0.87},
        ]
    }
    mock_memory.get_all.return_value = {
        "results": [
            {"id": "mem_1", "memory": "User likes Italian food", "metadata": {}},
            {"id": "mem_2", "memory": "User prefers morning meetings", "metadata": {}},
            {"id": "mem_3", "memory": "User works at Acme Corp", "metadata": {}},
        ]
    }
    mock_memory.delete.return_value = None
    mock_memory.delete_all.return_value = None

    with patch("digital_brain.memory.manager.Memory.from_config", return_value=mock_memory):
        yield mock_memory


@pytest.fixture()
def memory_manager(mock_mem0, settings) -> MemoryManager:
    """Return a MemoryManager backed by a mocked Mem0."""
    return MemoryManager(settings=settings)
