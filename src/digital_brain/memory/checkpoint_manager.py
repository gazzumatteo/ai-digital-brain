"""AgentCheckpointManager — persistent agent state for domain switching.

Inspired by muscle epigenetic memory, enables agents to save and restore
complete state across domain switches.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from redis.asyncio import Redis

if TYPE_CHECKING:
    from digital_brain.config import DistributedMemorySettings
    from digital_brain.memory.manager import MemoryManager

logger = logging.getLogger(__name__)


class AgentCheckpointManager:
    """Save and restore agent state using Redis-backed checkpoints."""

    def __init__(
        self,
        redis_client: Redis,
        memory_manager: MemoryManager,
        settings: DistributedMemorySettings,
    ) -> None:
        self._redis = redis_client
        self._memory = memory_manager
        self._settings = settings

    def _key(self, agent_id: str, domain: str) -> str:
        return f"checkpoint:{agent_id}:{domain}"

    async def save_checkpoint(self, agent_id: str, domain: str) -> str:
        """Save a complete agent state checkpoint.

        Returns:
            The Redis key where the checkpoint was stored.
        """
        # Gather local memories from Redis
        local_memories = []
        cursor = 0
        prefix = f"agent:{agent_id}:"
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
                    local_memories.append({"key": key_str, "value": value})
            if cursor == 0:
                break

        checkpoint = {
            "agent_id": agent_id,
            "domain": domain,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "local_memories": local_memories,
        }

        key = self._key(agent_id, domain)
        await self._redis.set(key, json.dumps(checkpoint))
        logger.info(
            "Saved checkpoint for %s in domain '%s' (%d local memories)",
            agent_id,
            domain,
            len(local_memories),
        )
        return key

    async def restore_checkpoint(self, agent_id: str, domain: str) -> bool:
        """Restore agent state from a checkpoint.

        Returns:
            True if checkpoint was found and restored, False otherwise.
        """
        key = self._key(agent_id, domain)
        raw = await self._redis.get(key)
        if raw is None:
            logger.warning("No checkpoint found for %s in domain '%s'", agent_id, domain)
            return False

        checkpoint = json.loads(raw)

        # Restore local memories
        for item in checkpoint.get("local_memories", []):
            redis_key = item["key"]
            raw_val = item["value"]
            value = json.dumps(raw_val) if not isinstance(raw_val, str) else raw_val
            await self._redis.set(redis_key, value, ex=self._settings.working_ttl)

        logger.info(
            "Restored checkpoint for %s from domain '%s' (%d memories)",
            agent_id,
            domain,
            len(checkpoint.get("local_memories", [])),
        )
        return True

    async def list_checkpoints(self, agent_id: str) -> list[dict]:
        """List all available checkpoints for an agent."""
        checkpoints = []
        cursor = 0
        prefix = f"checkpoint:{agent_id}:"
        while True:
            cursor, keys = await self._redis.scan(cursor, match=f"{prefix}*", count=100)
            for k in keys:
                raw = await self._redis.get(k)
                if raw:
                    data = json.loads(raw)
                    checkpoints.append(
                        {
                            "domain": data.get("domain", ""),
                            "timestamp": data.get("timestamp", ""),
                            "memory_count": len(data.get("local_memories", [])),
                        }
                    )
            if cursor == 0:
                break
        return checkpoints

    async def delete_checkpoint(self, agent_id: str, domain: str) -> bool:
        """Delete a checkpoint.

        Returns:
            True if deleted, False if not found.
        """
        key = self._key(agent_id, domain)
        result = await self._redis.delete(key)
        if result:
            logger.info("Deleted checkpoint for %s in domain '%s'", agent_id, domain)
        return bool(result)
