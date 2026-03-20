"""ImportanceScorer — biologically-inspired event importance scoring.

Inspired by hippocampal sharp-wave ripples, scores memory events across
four dimensions (novelty, relevance, salience, recency) and routes them
to the appropriate storage tier.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from digital_brain.config import DistributedMemorySettings
    from digital_brain.memory.manager import MemoryManager

# Regex for urgency / salience markers
_SALIENCE_PATTERN = re.compile(
    r"\b(urgent|deadline|critical|decide|important|asap|emergency|blocker|priority)\b",
    re.IGNORECASE,
)


class MemoryTier(str, Enum):
    EDGE = "edge"
    WORKING = "working"
    SEMANTIC = "semantic"


@dataclass
class MemoryEvent:
    content: str
    user_id: str
    agent_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context: dict = field(default_factory=dict)


class ImportanceScorer:
    """Score events across four dimensions and route to appropriate tier."""

    def __init__(
        self,
        settings: DistributedMemorySettings,
        memory_manager: MemoryManager,
    ) -> None:
        self._settings = settings
        self._memory = memory_manager

    def score(self, event: MemoryEvent) -> float:
        """Compute weighted importance score in [0, 1]."""
        s = self._settings
        raw = (
            s.novelty_weight * self._novelty(event)
            + s.relevance_weight * self._relevance(event)
            + s.salience_weight * self._salience(event)
            + s.recency_weight * self._recency(event)
        )
        return max(0.0, min(1.0, raw))

    def route(self, event: MemoryEvent) -> tuple[MemoryTier, float]:
        """Score and determine storage tier."""
        importance = self.score(event)
        if importance >= self._settings.semantic_threshold:
            return MemoryTier.SEMANTIC, importance
        if importance >= self._settings.working_threshold:
            return MemoryTier.WORKING, importance
        return MemoryTier.EDGE, importance

    def _novelty(self, event: MemoryEvent) -> float:
        """1.0 - max_similarity from existing memories."""
        result = self._memory.search(event.content, user_id=event.user_id, limit=3)
        if not result.results:
            return 1.0
        max_score = max(r.score or 0.0 for r in result.results)
        return max(0.0, 1.0 - max_score)

    def _relevance(self, event: MemoryEvent) -> float:
        """Compare event against goals in context."""
        goals = event.context.get("goals", [])
        if not goals:
            return 0.5  # neutral when no goals
        content_lower = event.content.lower()
        matches = sum(1 for g in goals if g.lower() in content_lower)
        return min(1.0, matches / len(goals))

    def _salience(self, event: MemoryEvent) -> float:
        """Detect urgency markers via regex."""
        matches = _SALIENCE_PATTERN.findall(event.content)
        return min(1.0, len(matches) * 0.3)

    def _recency(self, event: MemoryEvent) -> float:
        """Exponential decay: recent events score higher."""
        age_hours = (datetime.now(timezone.utc) - event.timestamp).total_seconds() / 3600
        return math.exp(-0.1 * age_hours)
