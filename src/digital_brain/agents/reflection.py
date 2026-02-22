"""ReflectionAgent — Digital Sleep / Memory Consolidation.

Inspired by NREM sleep consolidation, this agent:
  1. GATHERS recent episodic memories
  2. ANALYSES for patterns, contradictions, redundancies
  3. SYNTHESISES higher-level semantic insights
  4. PRUNES obsolete or duplicated memories
"""

from __future__ import annotations

import logging

from google.adk.agents import Agent

from digital_brain.config import get_settings
from digital_brain.memory.tools import (
    memory_delete,
    memory_get_all,
    memory_search,
    memory_store,
)

logger = logging.getLogger(__name__)

REFLECTION_INSTRUCTION = """\
You are a Memory Consolidation Agent performing "digital sleep" for user {user_id}.

Your job is to review recent memories and improve the memory store quality.

## Process

1. **GATHER** — Use `memory_get_all` to retrieve all memories for the user.

2. **ANALYSE** — Examine the memories and identify:
   - Recurring patterns (e.g. user mentioned Italian food 3 times)
   - Contradictions (e.g. "likes coffee" vs "quit coffee last week")
   - Redundant/duplicate memories
   - Outdated information

3. **SYNTHESISE** — For patterns you identify with confidence, create new
   high-level insight memories using `memory_store`. Prefix these with
   "[INSIGHT]" so they are distinguishable.
   Example: "[INSIGHT] User strongly prefers Italian cuisine (mentioned 5 times)"

4. **PRUNE** — Use `memory_delete` to remove:
   - Exact or near-exact duplicates (keep the most informative version)
   - Memories that are superseded by newer, contradictory information
   - Memories that have been fully absorbed into an insight

## Rules

- Only create insights when supported by at least {min_memories} source memories.
- When resolving contradictions, newer information wins.
- NEVER delete a memory if you are unsure — err on the side of keeping.
- Log a brief summary of actions taken at the end.

## Current configuration

- User: {user_id}
- Minimum memories for insight: {min_memories}
"""


def create_reflection_agent(model: str | None = None) -> Agent:
    """Create the Reflection (consolidation) Agent."""
    settings = get_settings()
    return Agent(
        name="reflection_agent",
        model=model or settings.llm.model,
        instruction=REFLECTION_INSTRUCTION,
        description="Consolidates and synthesises user memories during scheduled 'digital sleep'.",
        tools=[memory_get_all, memory_search, memory_store, memory_delete],
        output_key="reflection_summary",
    )
