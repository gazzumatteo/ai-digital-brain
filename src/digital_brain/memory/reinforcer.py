"""MemoryReinforcer — spaced repetition for memory consolidation.

Inspired by Kukushkin's cellular memory research, applies strength-based
reinforcement with interval doubling and decay-based pruning.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from digital_brain.config import DistributedMemorySettings
    from digital_brain.memory.manager import MemoryManager

logger = logging.getLogger(__name__)

# Default metadata for memories that lack reinforcement fields
_DEFAULT_METADATA: dict[str, Any] = {
    "strength": 0.5,
    "access_count": 0,
    "last_accessed": None,
    "spacing_interval": 1,  # hours
    "last_reinforced": None,
    "source_agent": None,
    "importance_score": 0.0,
}


class MemoryReinforcer:
    """Applies spaced repetition reinforcement to Mem0 memories."""

    def __init__(
        self,
        memory_manager: MemoryManager,
        settings: DistributedMemorySettings,
    ) -> None:
        self._memory = memory_manager
        self._settings = settings

    def reinforcement_cycle(self, user_id: str) -> dict[str, int]:
        """Run a full reinforcement cycle over all user memories.

        Returns:
            Dict with counts: {reinforced, decayed, pruned}.
        """
        all_memories = self._memory.get_all(user_id=user_id)
        stats = {"reinforced": 0, "decayed": 0, "pruned": 0}

        for entry in all_memories.results:
            metadata = self._ensure_metadata(entry.metadata or {})
            action = self._classify(metadata)

            if action == "reinforce":
                self._reinforce(entry.id, user_id, metadata)
                stats["reinforced"] += 1
            elif action == "decay":
                self._decay(entry.id, user_id, metadata)
                stats["decayed"] += 1
                # Check if decayed below prune threshold
                new_strength = metadata["strength"] - self._settings.decay_rate
                if new_strength < self._settings.prune_threshold:
                    self._prune(entry.id)
                    stats["pruned"] += 1

        logger.info("Reinforcement cycle for %s: %s", user_id, stats)
        return stats

    def _classify(self, metadata: dict) -> str:
        """Classify a memory for reinforcement, decay, or skip."""
        now = datetime.now(timezone.utc)
        last_reinforced = metadata.get("last_reinforced")
        spacing_interval = metadata.get("spacing_interval", 1)

        if last_reinforced is None:
            return "reinforce"

        if isinstance(last_reinforced, str):
            last_reinforced = datetime.fromisoformat(last_reinforced)

        hours_since = (now - last_reinforced).total_seconds() / 3600

        if hours_since >= spacing_interval:
            # Due for reinforcement if accessed recently
            access_count = metadata.get("access_count", 0)
            if access_count > 0:
                return "reinforce"
            return "decay"

        return "skip"

    def _reinforce(self, memory_id: str, user_id: str, metadata: dict) -> None:
        """Strengthen a memory and double its spacing interval."""
        now = datetime.now(timezone.utc).isoformat()
        strength = min(1.0, metadata.get("strength", 0.5) + 0.1)
        interval = min(
            self._settings.max_spacing_interval,
            metadata.get("spacing_interval", 1) * 2,
        )
        updated = {
            **metadata,
            "strength": strength,
            "spacing_interval": interval,
            "last_reinforced": now,
            "access_count": 0,  # reset after reinforcement
        }
        self._memory.add(
            f"[reinforcement update for {memory_id}]",
            user_id=user_id,
            metadata=updated,
            infer=False,
        )
        logger.debug("Reinforced %s: strength=%.2f interval=%dh", memory_id, strength, interval)

    def _decay(self, memory_id: str, user_id: str, metadata: dict) -> None:
        """Reduce memory strength by decay_rate."""
        strength = max(0.0, metadata.get("strength", 0.5) - self._settings.decay_rate)
        updated = {
            **metadata,
            "strength": strength,
        }
        self._memory.add(
            f"[decay update for {memory_id}]",
            user_id=user_id,
            metadata=updated,
            infer=False,
        )
        logger.debug("Decayed %s: strength=%.2f", memory_id, strength)

    def _prune(self, memory_id: str) -> None:
        """Delete a memory that has decayed below threshold."""
        self._memory.delete(memory_id)
        logger.info("Pruned memory %s (below threshold)", memory_id)

    def track_access(self, memory_id: str, user_id: str) -> None:
        """Record that a memory was accessed (increment access_count)."""
        # We update via Mem0's add with infer=False to update metadata
        now = datetime.now(timezone.utc).isoformat()
        self._memory.add(
            f"[access tracking for {memory_id}]",
            user_id=user_id,
            metadata={"last_accessed": now, "access_increment": True},
            infer=False,
        )

    @staticmethod
    def _ensure_metadata(metadata: dict) -> dict:
        """Fill missing reinforcement fields with defaults."""
        result = dict(_DEFAULT_METADATA)
        result.update(metadata)
        return result
