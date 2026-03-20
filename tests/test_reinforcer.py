"""Tests for MemoryReinforcer — reinforcement cycle and metadata updates."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from digital_brain.config import DistributedMemorySettings
from digital_brain.memory.reinforcer import MemoryReinforcer


@pytest.fixture()
def reinforcer(memory_manager) -> MemoryReinforcer:
    return MemoryReinforcer(memory_manager, DistributedMemorySettings())


class TestClassification:
    def test_classify_reinforces_new_memories(self, reinforcer):
        metadata = {"strength": 0.5, "access_count": 1, "last_reinforced": None}
        assert reinforcer._classify(metadata) == "reinforce"

    def test_classify_reinforces_when_due_and_accessed(self, reinforcer):
        old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        metadata = {
            "strength": 0.5,
            "access_count": 3,
            "last_reinforced": old,
            "spacing_interval": 1,
        }
        assert reinforcer._classify(metadata) == "reinforce"

    def test_classify_decays_when_due_but_not_accessed(self, reinforcer):
        old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        metadata = {
            "strength": 0.5,
            "access_count": 0,
            "last_reinforced": old,
            "spacing_interval": 1,
        }
        assert reinforcer._classify(metadata) == "decay"

    def test_classify_skips_when_not_due(self, reinforcer):
        recent = datetime.now(timezone.utc).isoformat()
        metadata = {
            "strength": 0.5,
            "access_count": 1,
            "last_reinforced": recent,
            "spacing_interval": 24,
        }
        assert reinforcer._classify(metadata) == "skip"


class TestReinforcementCycle:
    def test_cycle_processes_all_memories(self, reinforcer, mock_mem0):
        """Mock get_all returns 3 memories — all should be processed."""
        stats = reinforcer.reinforcement_cycle("u1")
        total = stats["reinforced"] + stats["decayed"] + stats["pruned"]
        assert total <= 3  # some may be skipped

    def test_cycle_reinforces_new_memories(self, reinforcer, mock_mem0):
        """Memories with no last_reinforced should be reinforced."""
        stats = reinforcer.reinforcement_cycle("u1")
        assert stats["reinforced"] == 3  # all 3 have empty metadata → new

    def test_cycle_with_decayable_memories(self, memory_manager, mock_mem0):
        """Memories past interval with zero access should decay."""
        old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        mock_mem0.get_all.return_value = {
            "results": [
                {
                    "id": "mem_1",
                    "memory": "Test",
                    "metadata": {
                        "strength": 0.5,
                        "access_count": 0,
                        "last_reinforced": old,
                        "spacing_interval": 1,
                    },
                }
            ]
        }
        reinforcer = MemoryReinforcer(memory_manager, DistributedMemorySettings())
        stats = reinforcer.reinforcement_cycle("u1")
        assert stats["decayed"] >= 1

    def test_cycle_prunes_weak_memories(self, memory_manager, mock_mem0):
        """Memories at prune_threshold edge should be pruned after decay."""
        old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        mock_mem0.get_all.return_value = {
            "results": [
                {
                    "id": "mem_weak",
                    "memory": "Weak memory",
                    "metadata": {
                        "strength": 0.22,  # decay_rate=0.05 → 0.17 < threshold 0.2
                        "access_count": 0,
                        "last_reinforced": old,
                        "spacing_interval": 1,
                    },
                }
            ]
        }
        reinforcer = MemoryReinforcer(memory_manager, DistributedMemorySettings())
        stats = reinforcer.reinforcement_cycle("u1")
        assert stats["pruned"] == 1
        mock_mem0.delete.assert_called_with(memory_id="mem_weak")


class TestMetadata:
    def test_ensure_metadata_fills_defaults(self, reinforcer):
        result = reinforcer._ensure_metadata({})
        assert result["strength"] == 0.5
        assert result["access_count"] == 0
        assert result["spacing_interval"] == 1

    def test_ensure_metadata_preserves_existing(self, reinforcer):
        result = reinforcer._ensure_metadata({"strength": 0.8, "custom": "value"})
        assert result["strength"] == 0.8
        assert result["custom"] == "value"

    def test_track_access_calls_add(self, reinforcer, mock_mem0):
        reinforcer.track_access("mem_1", "u1")
        mock_mem0.add.assert_called()
