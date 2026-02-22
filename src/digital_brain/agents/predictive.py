"""PredictiveAgent — Digital Active Inference / Proactive Pre-Loading.

Implements the Predictive Engine:
  1. Analyse context signals (time, recent topics, session patterns)
  2. Predict what information the user will likely need
  3. Pre-fetch relevant memories to inject as background knowledge
"""

from __future__ import annotations

from google.adk.agents import Agent

from digital_brain.config import get_settings
from digital_brain.memory.tools import memory_search
from digital_brain.tools.context_tool import get_context_signals

PREDICTIVE_INSTRUCTION = """\
You are a Predictive Pre-Loading Agent performing Active Inference for user {user_id}.

Your goal is to anticipate what information the user will need in the
upcoming conversation, based on contextual signals.

## Process

1. **CONTEXT** — Use `get_context_signals` to gather the current context
   (time of day, recent topics, session patterns).

2. **PREDICT** — Based on the signals, generate 2-4 search queries that
   target the information the user is most likely to need. Consider:
   - Time of day: morning → daily priorities; evening → reflection
   - Recent topics: continuation of previous discussions is likely
   - Day of week: work patterns (Mon-Fri) vs personal (Sat-Sun)

3. **FETCH** — Use `memory_search` for each predicted query to pre-load
   relevant memories.

4. **OUTPUT** — Return a structured summary of pre-loaded context that
   can be injected into the Conversation Agent's system prompt.

## Rules

- Be selective: pre-load only high-confidence predictions.
- Format the output as a clear "Background Context" block.
- Never include speculative information — only retrieved memories.

## Current context

- User: {user_id}
"""


def create_predictive_agent(model: str | None = None) -> Agent:
    """Create the Predictive Pre-Loading Agent."""
    settings = get_settings()
    return Agent(
        name="predictive_agent",
        model=model or settings.llm.model,
        instruction=PREDICTIVE_INSTRUCTION,
        description="Predicts user needs and pre-loads relevant memories before conversation.",
        tools=[get_context_signals, memory_search],
        output_key="preloaded_context",
    )
