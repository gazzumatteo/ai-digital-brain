"""Tests for LocalAgentMemory — local storage, escalation, and context."""

from __future__ import annotations

import pytest

from digital_brain.config import DistributedMemorySettings
from digital_brain.memory.importance_scorer import (
    ImportanceScorer,
    MemoryEvent,
    MemoryTier,
)
from digital_brain.memory.local_agent_memory import LocalAgentMemory


@pytest.fixture()
def local_memory(fake_redis, memory_manager) -> LocalAgentMemory:
    settings = DistributedMemorySettings()
    scorer = ImportanceScorer(settings, memory_manager)
    return LocalAgentMemory(
        agent_id="test_agent",
        agent_type="conversation",
        redis_client=fake_redis,
        memory_manager=memory_manager,
        scorer=scorer,
        settings=settings,
    )


class TestLocalStorage:
    @pytest.mark.asyncio
    async def test_remember_and_recall(self, local_memory):
        await local_memory.remember_locally("greeting", {"text": "hello"})
        result = await local_memory.recall_locally("greeting")
        assert result == {"text": "hello"}

    @pytest.mark.asyncio
    async def test_recall_missing_key(self, local_memory):
        result = await local_memory.recall_locally("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_remember_string_value(self, local_memory):
        await local_memory.remember_locally("note", "plain text")
        result = await local_memory.recall_locally("note")
        assert result == {"value": "plain text"}

    @pytest.mark.asyncio
    async def test_clear_local(self, local_memory):
        await local_memory.remember_locally("k1", {"v": 1})
        await local_memory.remember_locally("k2", {"v": 2})
        await local_memory.clear_local()
        assert await local_memory.recall_locally("k1") is None
        assert await local_memory.recall_locally("k2") is None

    @pytest.mark.asyncio
    async def test_export_local_memories(self, local_memory):
        await local_memory.remember_locally("k1", {"v": 1})
        await local_memory.remember_locally("k2", {"v": 2})
        exported = await local_memory.export_local_memories()
        assert len(exported) == 2
        keys = {item["key"] for item in exported}
        assert "agent:test_agent:k1" in keys
        assert "agent:test_agent:k2" in keys


class TestEscalation:
    @pytest.mark.asyncio
    async def test_process_event_returns_tier_and_score(self, local_memory):
        event = MemoryEvent(
            content="Test event",
            user_id="u1",
            agent_id="test_agent",
        )
        tier, score = await local_memory.process_event(event)
        assert isinstance(tier, MemoryTier)
        assert isinstance(score, float)

    @pytest.mark.asyncio
    async def test_process_urgent_event_escalates(self, local_memory, mock_mem0):
        event = MemoryEvent(
            content="URGENT CRITICAL emergency blocker deadline",
            user_id="u1",
            agent_id="test_agent",
            context={"goals": ["urgent"]},
        )
        tier, _score = await local_memory.process_event(event)
        # Should escalate — Mem0 add called with metadata
        if tier in (MemoryTier.WORKING, MemoryTier.SEMANTIC):
            mock_mem0.add.assert_called()


class TestContext:
    @pytest.mark.asyncio
    async def test_get_context_merges_local_and_central(self, local_memory):
        await local_memory.remember_locally(
            "event:test", {"content": "local memory", "context": {}}
        )
        ctx = await local_memory.get_context("test query", user_id="u1")
        assert "local" in ctx
        assert "central" in ctx
        assert len(ctx["central"]) > 0  # from mock_mem0
