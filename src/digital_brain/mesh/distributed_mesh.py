"""DistributedMemoryMesh — facade wiring all four biological patterns.

Provides a unified API for agent registration, event processing,
reinforcement, domain switching, and querying.
"""

from __future__ import annotations

import logging
from typing import Any

from redis.asyncio import Redis

from digital_brain.config import Settings, get_settings
from digital_brain.memory.checkpoint_manager import AgentCheckpointManager
from digital_brain.memory.importance_scorer import ImportanceScorer, MemoryEvent
from digital_brain.memory.local_agent_memory import LocalAgentMemory
from digital_brain.memory.manager import MemoryManager
from digital_brain.memory.reinforcer import MemoryReinforcer

logger = logging.getLogger(__name__)


class DistributedMemoryMesh:
    """Integration facade for the distributed memory mesh."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._redis: Redis | None = None
        self._memory: MemoryManager | None = None
        self._scorer: ImportanceScorer | None = None
        self._reinforcer: MemoryReinforcer | None = None
        self._checkpoint: AgentCheckpointManager | None = None
        self._agents: dict[str, LocalAgentMemory] = {}

    async def connect(self) -> None:
        """Initialize Redis connection and all subsystems."""
        rs = self._settings.redis
        self._redis = Redis(
            host=rs.host,
            port=rs.port,
            db=rs.db,
            password=rs.password or None,
            decode_responses=True,
        )
        self._memory = MemoryManager(settings=self._settings)
        self._scorer = ImportanceScorer(self._settings.distributed, self._memory)
        self._reinforcer = MemoryReinforcer(self._memory, self._settings.distributed)
        self._checkpoint = AgentCheckpointManager(
            self._redis, self._memory, self._settings.distributed
        )
        logger.info("DistributedMemoryMesh connected (redis=%s:%d)", rs.host, rs.port)

    async def close(self) -> None:
        """Cleanup Redis connection."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None
        logger.info("DistributedMemoryMesh closed")

    def register_agent(self, agent_id: str, agent_type: str) -> LocalAgentMemory:
        """Register an agent and return its local memory instance."""
        if not self._redis or not self._memory or not self._scorer:
            raise RuntimeError("Mesh not connected. Call connect() first.")

        agent_mem = LocalAgentMemory(
            agent_id=agent_id,
            agent_type=agent_type,
            redis_client=self._redis,
            memory_manager=self._memory,
            scorer=self._scorer,
            settings=self._settings.distributed,
        )
        self._agents[agent_id] = agent_mem
        logger.info("Registered agent %s (type=%s)", agent_id, agent_type)
        return agent_mem

    async def process_event(self, event: MemoryEvent, agent_id: str) -> dict[str, Any]:
        """Process an event through a registered agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not registered")

        tier, score = await agent.process_event(event)
        return {"tier": tier.value, "score": score, "agent_id": agent_id}

    async def run_reinforcement(self, user_id: str) -> dict[str, int]:
        """Run a reinforcement cycle for a user's memories."""
        if not self._reinforcer:
            raise RuntimeError("Mesh not connected. Call connect() first.")
        return self._reinforcer.reinforcement_cycle(user_id)

    async def switch_domain(
        self, agent_id: str, old_domain: str, new_domain: str
    ) -> dict[str, Any]:
        """Save current agent state and restore from a different domain."""
        if not self._checkpoint:
            raise RuntimeError("Mesh not connected. Call connect() first.")

        # Save current state
        await self._checkpoint.save_checkpoint(agent_id, old_domain)

        # Clear local memory
        agent = self._agents.get(agent_id)
        if agent:
            await agent.clear_local()

        # Restore from new domain
        restored = await self._checkpoint.restore_checkpoint(agent_id, new_domain)

        return {
            "agent_id": agent_id,
            "saved_domain": old_domain,
            "restored_domain": new_domain,
            "restored": restored,
        }

    async def query(self, query: str, user_id: str, agent_id: str | None = None) -> dict[str, Any]:
        """Unified query across local and central memory with access tracking."""
        if not self._reinforcer or not self._memory:
            raise RuntimeError("Mesh not connected. Call connect() first.")

        result: dict[str, Any] = {"query": query, "user_id": user_id}

        # Agent-specific local + central context
        if agent_id and agent_id in self._agents:
            context = await self._agents[agent_id].get_context(query, user_id)
            result["local"] = context["local"]
            result["central"] = context["central"]
        else:
            # Central only
            search = self._memory.search(query, user_id=user_id, limit=5)
            result["central"] = [{"memory": r.memory, "score": r.score} for r in search.results]

        # Track access for returned memories
        for mem in result.get("central", []):
            if isinstance(mem, dict) and "memory" in mem:
                self._reinforcer.track_access(mem["memory"], user_id)

        return result
