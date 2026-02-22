"""Pydantic models for memory entities."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    INSIGHT = "insight"


class MemoryEntry(BaseModel):
    id: str
    memory: str
    user_id: str | None = None
    score: float | None = None
    memory_type: MemoryType = MemoryType.EPISODIC
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_count: int = Field(default=1, ge=1)
    created_at: datetime | None = None
    metadata: dict | None = None


class MemorySearchResult(BaseModel):
    results: list[MemoryEntry] = Field(default_factory=list)
    total: int = 0
