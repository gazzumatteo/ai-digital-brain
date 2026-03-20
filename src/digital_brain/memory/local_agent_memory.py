"""LocalAgentMemory — per-agent Redis-backed autonomous memory.

Inspired by the enteric nervous system, each agent maintains local memory
and only escalates high-importance events to central Mem0 storage.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from redis.asyncio import Redis

from digital_brain.memory.importance_scorer import MemoryEvent, MemoryTier

if TYPE_CHECKING:
    from digital_brain.config import DistributedMemorySettings
    from digital_brain.memory.importance_scorer import ImportanceScorer
    from digital_brain.memory.manager import MemoryManager

logger = logging.getLogger(__name__)


class LocalAgentMemory:
    """Autonomous per-agent memory with local Redis storage and escalation."""

    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        redis_client: Redis,
        memory_manager: MemoryManager,
        scorer: ImportanceScorer,
        settings: DistributedMemorySettings,
    ) -> None:
        self._agent_id = agent_id
        self._agent_type = agent_type
        self._redis = redis_client
        self._memory = memory_manager
        self._scorer = scorer
        self._settings = settings

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def _key(self, key: str) -> str:
        return f"agent:{self._agent_id}:{key}"

    async def remember_locally(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value in local Redis-backed memory."""
        payload = json.dumps(value) if not isinstance(value, str) else value
        effective_ttl = ttl or self._settings.edge_ttl
        await self._redis.set(self._key(key), payload, ex=effective_ttl)

    async def recall_locally(self, key: str) -> dict | None:
        """Retrieve a value from local memory."""
        raw = await self._redis.get(self._key(key))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {"value": raw.decode() if isinstance(raw, bytes) else raw}

    async def process_event(self, event: MemoryEvent) -> tuple[MemoryTier, float]:
        """Process an event: store locally, score, and escalate if important."""
        # Always store locally
        await self.remember_locally(
            f"event:{event.timestamp.isoformat()}",
            {"content": event.content, "context": event.context},
            ttl=self._settings.edge_ttl,
        )

        # Score and route
        tier, score = self._scorer.route(event)

        # Escalate to central Mem0 for working and semantic tiers
        if tier in (MemoryTier.WORKING, MemoryTier.SEMANTIC):
            self._memory.add(
                event.content,
                user_id=event.user_id,
                metadata={
                    "source_agent": self._agent_id,
                    "agent_type": self._agent_type,
                    "importance_score": score,
                    "tier": tier.value,
                },
            )
            logger.info(
                "Escalated event to %s (score=%.2f, agent=%s)",
                tier.value,
                score,
                self._agent_id,
            )

        return tier, score

    async def get_context(self, query: str, user_id: str) -> dict:
        """Retrieve context: local memories first, then central."""
        # Gather local memories
        local_keys = []
        cursor = 0
        prefix = self._key("event:")
        while True:
            cursor, keys = await self._redis.scan(cursor, match=f"{prefix}*", count=50)
            local_keys.extend(keys)
            if cursor == 0:
                break

        local_memories = []
        for k in local_keys[:20]:  # limit
            raw = await self._redis.get(k)
            if raw:
                try:
                    local_memories.append(json.loads(raw))
                except (json.JSONDecodeError, TypeError):
                    pass

        # Central search
        central = self._memory.search(query, user_id=user_id, limit=5)

        return {
            "local": local_memories,
            "central": [{"memory": r.memory, "score": r.score} for r in central.results],
        }

    async def export_local_memories(self) -> list[dict]:
        """Export all local memories for checkpointing."""
        result = []
        cursor = 0
        prefix = self._key("")
        while True:
            cursor, keys = await self._redis.scan(cursor, match=f"{prefix}*", count=100)
            for k in keys:
                raw = await self._redis.get(k)
                if raw:
                    key_str = k.decode() if isinstance(k, bytes) else k
                    try:
                        value = json.loads(raw)
                    except (json.JSONDecodeError, TypeError):
                        value = raw.decode() if isinstance(raw, bytes) else raw
                    result.append({"key": key_str, "value": value})
            if cursor == 0:
                break
        return result

    async def clear_local(self) -> None:
        """Clear all local memories for this agent."""
        cursor = 0
        prefix = self._key("")
        while True:
            cursor, keys = await self._redis.scan(cursor, match=f"{prefix}*", count=100)
            if keys:
                await self._redis.delete(*keys)
            if cursor == 0:
                break
