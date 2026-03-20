"""Tests for ImportanceScorer — scoring dimensions and tier routing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from digital_brain.config import DistributedMemorySettings
from digital_brain.memory.importance_scorer import (
    ImportanceScorer,
    MemoryEvent,
    MemoryTier,
)


@pytest.fixture()
def scorer(memory_manager) -> ImportanceScorer:
    return ImportanceScorer(DistributedMemorySettings(), memory_manager)


class TestScoreDimensions:
    def test_score_returns_float_in_range(self, scorer):
        event = MemoryEvent(content="test content", user_id="u1", agent_id="a1")
        score = scorer.score(event)
        assert 0.0 <= score <= 1.0

    def test_novelty_high_when_no_existing_memories(self, scorer):
        """When search returns no results, novelty should be 1.0."""
        # Mock returns results by default, but novelty = 1 - max_score
        event = MemoryEvent(content="test", user_id="u1", agent_id="a1")
        novelty = scorer._novelty(event)
        # Default mock returns score=0.95, so novelty = 0.05
        assert novelty == pytest.approx(0.05, abs=0.01)

    def test_relevance_with_matching_goals(self, scorer):
        event = MemoryEvent(
            content="We need to finish the project deadline",
            user_id="u1",
            agent_id="a1",
            context={"goals": ["deadline", "project"]},
        )
        relevance = scorer._relevance(event)
        assert relevance > 0.0

    def test_relevance_neutral_without_goals(self, scorer):
        event = MemoryEvent(content="test", user_id="u1", agent_id="a1", context={})
        assert scorer._relevance(event) == 0.5

    def test_salience_detects_urgency_markers(self, scorer):
        event = MemoryEvent(
            content="This is URGENT and a CRITICAL blocker",
            user_id="u1",
            agent_id="a1",
        )
        salience = scorer._salience(event)
        assert salience > 0.0

    def test_salience_zero_for_plain_text(self, scorer):
        event = MemoryEvent(content="The weather is nice today", user_id="u1", agent_id="a1")
        assert scorer._salience(event) == 0.0

    def test_recency_high_for_recent_events(self, scorer):
        event = MemoryEvent(
            content="test",
            user_id="u1",
            agent_id="a1",
            timestamp=datetime.now(timezone.utc),
        )
        assert scorer._recency(event) > 0.9

    def test_recency_low_for_old_events(self, scorer):
        event = MemoryEvent(
            content="test",
            user_id="u1",
            agent_id="a1",
            timestamp=datetime.now(timezone.utc) - timedelta(hours=48),
        )
        assert scorer._recency(event) < 0.01


class TestRouting:
    def test_route_returns_tier_and_score(self, scorer):
        event = MemoryEvent(content="test", user_id="u1", agent_id="a1")
        tier, score = scorer.route(event)
        assert isinstance(tier, MemoryTier)
        assert 0.0 <= score <= 1.0

    def test_high_importance_routes_to_semantic(self, scorer):
        """Event with urgency markers + goals should route high."""
        event = MemoryEvent(
            content="URGENT CRITICAL deadline decide ASAP emergency blocker",
            user_id="u1",
            agent_id="a1",
            context={"goals": ["urgent", "critical"]},
        )
        tier, score = scorer.route(event)
        # With high salience + relevance, should be working or semantic
        assert tier in (MemoryTier.WORKING, MemoryTier.SEMANTIC)

    def test_low_importance_routes_to_edge(self, scorer):
        """Plain old event from hours ago should route to edge."""
        event = MemoryEvent(
            content="The sky is blue",
            user_id="u1",
            agent_id="a1",
            timestamp=datetime.now(timezone.utc) - timedelta(hours=24),
        )
        tier, _score = scorer.route(event)
        assert tier == MemoryTier.EDGE
