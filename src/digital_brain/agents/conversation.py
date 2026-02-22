"""ConversationAgent — Memory-augmented dialogue agent.

Implements the Mnemonic Loop:
  1. RETRIEVE — search memory before responding
  2. GENERATE — respond with memory context
  3. STORE    — extract and save new facts (async, non-blocking)
"""

from __future__ import annotations

from google.adk.agents import Agent

from digital_brain.config import get_settings
from digital_brain.memory.tools import memory_search, memory_store

CONVERSATION_INSTRUCTION = """\
You are a personal assistant with persistent long-term memory.

## Core behaviour

1. **Before answering**, ALWAYS use `memory_search` to check if you already
   know something relevant about the user or the topic. Use the user_id
   provided in the conversation context.

2. **Answer** the user's question naturally. Weave in recalled memories when
   relevant — but don't announce "I searched my memory" unless the user asks.

3. **After answering**, evaluate whether the conversation contained new facts,
   preferences, decisions, or goals worth remembering. If so, use
   `memory_store` to save each distinct fact as a concise statement.

## Guidelines

- Be concise and helpful.
- Never invent memories — only use what `memory_search` returns.
- When storing, prefer atomic facts ("User prefers morning meetings")
  over vague summaries ("Had a conversation about scheduling").
- Respect privacy: do not store information the user asks you to forget.

## Context

The current user_id is: {user_id}
"""


def create_conversation_agent(model: str | None = None) -> Agent:
    """Create the memory-augmented Conversation Agent."""
    settings = get_settings()
    return Agent(
        name="conversation_agent",
        model=model or settings.llm.model,
        instruction=CONVERSATION_INSTRUCTION,
        description="A personal assistant that remembers user preferences and past interactions.",
        tools=[memory_search, memory_store],
        output_key="last_response",
    )
