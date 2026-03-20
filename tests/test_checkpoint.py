"""Tests for AgentCheckpointManager — save/restore round-trip."""

from __future__ import annotations

import pytest

from digital_brain.config import DistributedMemorySettings
from digital_brain.memory.checkpoint_manager import AgentCheckpointManager


@pytest.fixture()
def checkpoint_mgr(fake_redis, memory_manager) -> AgentCheckpointManager:
    return AgentCheckpointManager(
        redis_client=fake_redis,
        memory_manager=memory_manager,
        settings=DistributedMemorySettings(),
    )


class TestSaveRestore:
    @pytest.mark.asyncio
    async def test_save_creates_checkpoint(self, checkpoint_mgr, fake_redis):
        # Seed some agent-local data
        await fake_redis.set("agent:a1:key1", '{"val": 1}')
        await fake_redis.set("agent:a1:key2", '{"val": 2}')

        key = await checkpoint_mgr.save_checkpoint("a1", "domain_x")
        assert key == "checkpoint:a1:domain_x"

        # Checkpoint should exist in Redis
        raw = await fake_redis.get(key)
        assert raw is not None

    @pytest.mark.asyncio
    async def test_restore_returns_true_when_found(self, checkpoint_mgr, fake_redis):
        await fake_redis.set("agent:a1:data", '{"v": 42}')
        await checkpoint_mgr.save_checkpoint("a1", "domain_x")

        # Clear agent data
        await fake_redis.delete("agent:a1:data")

        result = await checkpoint_mgr.restore_checkpoint("a1", "domain_x")
        assert result is True

        # Data should be restored
        restored = await fake_redis.get("agent:a1:data")
        assert restored is not None

    @pytest.mark.asyncio
    async def test_restore_returns_false_when_not_found(self, checkpoint_mgr):
        result = await checkpoint_mgr.restore_checkpoint("nonexistent", "domain")
        assert result is False

    @pytest.mark.asyncio
    async def test_round_trip_preserves_data(self, checkpoint_mgr, fake_redis):
        await fake_redis.set("agent:bot:config", '{"mode": "active"}')
        await checkpoint_mgr.save_checkpoint("bot", "production")

        # Wipe and restore
        await fake_redis.delete("agent:bot:config")
        assert await fake_redis.get("agent:bot:config") is None

        await checkpoint_mgr.restore_checkpoint("bot", "production")
        restored = await fake_redis.get("agent:bot:config")
        assert restored is not None
        assert "active" in restored


class TestListDelete:
    @pytest.mark.asyncio
    async def test_list_checkpoints(self, checkpoint_mgr, fake_redis):
        await fake_redis.set("agent:a1:k1", '"v1"')
        await checkpoint_mgr.save_checkpoint("a1", "domain_a")
        await checkpoint_mgr.save_checkpoint("a1", "domain_b")

        checkpoints = await checkpoint_mgr.list_checkpoints("a1")
        assert len(checkpoints) == 2
        domains = {c["domain"] for c in checkpoints}
        assert domains == {"domain_a", "domain_b"}

    @pytest.mark.asyncio
    async def test_delete_checkpoint(self, checkpoint_mgr, fake_redis):
        await checkpoint_mgr.save_checkpoint("a1", "to_delete")
        deleted = await checkpoint_mgr.delete_checkpoint("a1", "to_delete")
        assert deleted is True

        # Should be gone
        deleted_again = await checkpoint_mgr.delete_checkpoint("a1", "to_delete")
        assert deleted_again is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, checkpoint_mgr):
        result = await checkpoint_mgr.delete_checkpoint("nope", "nope")
        assert result is False
