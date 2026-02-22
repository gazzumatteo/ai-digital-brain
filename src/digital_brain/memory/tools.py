"""ADK-compatible tool functions for memory operations.

These plain Python functions are auto-wrapped as FunctionTool by Google ADK.
The docstrings, parameter names, and type hints are what the LLM reads to
decide when and how to call each tool.
"""

from __future__ import annotations

from digital_brain.memory.manager import MemoryManager

_manager: MemoryManager | None = None


def _get_manager() -> MemoryManager:
    global _manager
    if _manager is None:
        _manager = MemoryManager()
    return _manager


def set_memory_manager(manager: MemoryManager) -> None:
    """Allow dependency injection (e.g. for tests)."""
    global _manager
    _manager = manager


def memory_store(content: str, user_id: str, category: str = "") -> dict:
    """Save important information about the user to long-term memory.

    Use this tool whenever the user shares personal facts, preferences,
    decisions, goals, or any information worth remembering across sessions.

    Args:
        content: The information to save (a concise fact or preference).
        user_id: The unique identifier of the user.
        category: Optional category tag (e.g. 'food', 'work', 'health').

    Returns:
        A dict confirming the memory was saved.
    """
    metadata = {"category": category} if category else None
    result = _get_manager().add(content, user_id=user_id, metadata=metadata)
    return {"status": "saved", "result": str(result)}


def memory_search(query: str, user_id: str, limit: int = 5) -> dict:
    """Search through the user's stored memories for relevant information.

    Use this tool BEFORE answering to check if you already know something
    about the user or the topic they are asking about.

    Args:
        query: The search query describing the information you need.
        user_id: The unique identifier of the user.
        limit: Maximum number of memories to return (default 5).

    Returns:
        A dict with matching memories or a message if none found.
    """
    result = _get_manager().search(query, user_id=user_id, limit=limit)
    if result.results:
        memories = "\n".join(f"- {m.memory}" for m in result.results)
        return {"status": "found", "count": result.total, "memories": memories}
    return {"status": "no_memories", "message": "No relevant memories found."}


def memory_get_all(user_id: str) -> dict:
    """Retrieve all stored memories for a user.

    Use this tool to get a complete overview of what you know about a user.

    Args:
        user_id: The unique identifier of the user.

    Returns:
        A dict containing all memories for the user.
    """
    result = _get_manager().get_all(user_id=user_id)
    if result.results:
        memories = "\n".join(f"- [{m.id}] {m.memory}" for m in result.results)
        return {"status": "found", "count": result.total, "memories": memories}
    return {"status": "empty", "message": "No memories stored for this user."}


def memory_delete(memory_id: str) -> dict:
    """Delete a specific memory by its ID.

    Use this tool when a memory is outdated, incorrect, or the user
    explicitly asks to forget something.

    Args:
        memory_id: The unique identifier of the memory to delete.

    Returns:
        A dict confirming the deletion.
    """
    _get_manager().delete(memory_id=memory_id)
    return {"status": "deleted", "memory_id": memory_id}
