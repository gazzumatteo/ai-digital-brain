"""MemoryManager — Mem0 wrapper with configuration from Settings."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from mem0 import Memory

from digital_brain.config import Settings, get_settings
from digital_brain.memory.schemas import MemoryEntry, MemorySearchResult

logger = logging.getLogger(__name__)


class MemoryManager:
    """High-level wrapper around Mem0 Memory, configured from application settings."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._memory = Memory.from_config(config_dict=self._build_config())
        logger.info("MemoryManager initialised (provider=%s)", self._settings.llm.provider)

    def _build_config(self) -> dict[str, Any]:
        s = self._settings
        config: dict[str, Any] = {
            "version": "v1.1",
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": s.qdrant.collection,
                    "host": s.qdrant.host,
                    "port": s.qdrant.port,
                    "embedding_model_dims": s.embedder.dims,
                },
            },
        }

        # LLM config
        if s.llm.provider == "ollama":
            config["llm"] = {
                "provider": "ollama",
                "config": {
                    "model": s.llm.model,
                    "temperature": 0,
                    "max_tokens": 2000,
                    "ollama_base_url": s.llm.ollama_base_url,
                },
            }
        elif s.llm.provider == "openai":
            config["llm"] = {
                "provider": "openai",
                "config": {
                    "model": s.llm.model,
                    "temperature": 0,
                },
            }
        # gemini — Mem0 supports it natively
        elif s.llm.provider == "gemini":
            config["llm"] = {
                "provider": "gemini",
                "config": {
                    "model": s.llm.model,
                    "temperature": 0,
                },
            }

        # Embedder config
        if s.embedder.provider == "ollama":
            config["embedder"] = {
                "provider": "ollama",
                "config": {
                    "model": s.embedder.model,
                    "ollama_base_url": s.llm.ollama_base_url,
                },
            }
        elif s.embedder.provider == "openai":
            config["embedder"] = {
                "provider": "openai",
                "config": {
                    "model": s.embedder.model,
                    "embedding_dims": s.embedder.dims,
                },
            }
        elif s.embedder.provider == "gemini":
            config["embedder"] = {
                "provider": "gemini",
                "config": {
                    "model": s.embedder.model,
                    "embedding_dims": s.embedder.dims,
                },
            }

        # Optional graph store
        if s.neo4j.enabled:
            config["graph_store"] = {
                "provider": "neo4j",
                "config": {
                    "url": s.neo4j.url,
                    "username": s.neo4j.username,
                    "password": s.neo4j.password,
                },
            }

        return config

    # --- Core operations ---

    def add(
        self,
        messages: str | list[dict[str, str]],
        user_id: str,
        metadata: dict | None = None,
        infer: bool = True,
    ) -> dict:
        """Store memories extracted from messages."""
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        result = self._memory.add(messages, user_id=user_id, metadata=metadata, infer=infer)
        logger.debug("memory.add user_id=%s result=%s", user_id, result)
        return result

    def search(self, query: str, user_id: str, limit: int = 5) -> MemorySearchResult:
        """Semantic search over a user's memories."""
        raw = self._memory.search(query, user_id=user_id, limit=limit)
        entries = [
            MemoryEntry(
                id=m.get("id", ""),
                memory=m.get("memory", ""),
                user_id=user_id,
                score=m.get("score"),
                metadata=m.get("metadata"),
            )
            for m in raw.get("results", [])
        ]
        return MemorySearchResult(results=entries, total=len(entries))

    def get_all(self, user_id: str, limit: int = 100) -> MemorySearchResult:
        """Return all memories for a user."""
        raw = self._memory.get_all(user_id=user_id, limit=limit)
        entries = [
            MemoryEntry(
                id=m.get("id", ""),
                memory=m.get("memory", ""),
                user_id=user_id,
                metadata=m.get("metadata"),
            )
            for m in raw.get("results", [])
        ]
        return MemorySearchResult(results=entries, total=len(entries))

    def delete(self, memory_id: str) -> None:
        """Delete a single memory by id."""
        self._memory.delete(memory_id=memory_id)
        logger.info("Deleted memory %s", memory_id)

    def delete_all(self, user_id: str) -> None:
        """Delete all memories for a user (right to be forgotten)."""
        self._memory.delete_all(user_id=user_id)
        logger.info("Deleted all memories for user %s", user_id)

    def get_recent(self, user_id: str, hours: int = 24) -> MemorySearchResult:
        """Return memories created in the last N hours.

        Falls back to get_all with client-side filtering since Mem0 does not
        natively support time-range queries.
        """
        all_memories = self.get_all(user_id=user_id, limit=500)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent = [m for m in all_memories.results if m.created_at is None or m.created_at >= cutoff]
        return MemorySearchResult(results=recent, total=len(recent))
