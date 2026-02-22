"""API routes for the Digital Brain."""

from __future__ import annotations

import logging
import re
from typing import Callable

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from digital_brain.agents.orchestrator import DigitalBrainOrchestrator
from digital_brain.memory.manager import MemoryManager
from digital_brain.metrics import metrics

logger = logging.getLogger(__name__)

# Allowed user_id pattern: alphanumeric, hyphens, underscores (1-128 chars)
_USER_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")


def _validate_user_id(user_id: str) -> str:
    """Validate user_id to prevent injection or path-traversal attacks."""
    if not _USER_ID_RE.match(user_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid user_id: must be 1-128 alphanumeric, hyphen, or underscore characters.",
        )
    return user_id


# --- Request / Response models ---


class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: str | None = None
    enable_prediction: bool = Field(default=True)

    @field_validator("user_id")
    @classmethod
    def check_user_id(cls, v: str) -> str:
        if not _USER_ID_RE.match(v):
            raise ValueError("user_id must be 1-128 alphanumeric/hyphen/underscore characters")
        return v

    @field_validator("message")
    @classmethod
    def check_message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message must not be empty")
        return v


class ChatResponse(BaseModel):
    response: str
    user_id: str
    session_id: str | None = None


class ReflectResponse(BaseModel):
    summary: str
    user_id: str


class MemoryListResponse(BaseModel):
    memories: list[dict]
    total: int
    user_id: str


class DeleteResponse(BaseModel):
    status: str


# --- Router factory ---


def create_router(get_orchestrator: Callable[[], DigitalBrainOrchestrator]) -> APIRouter:
    router = APIRouter()

    @router.post("/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest) -> ChatResponse:
        """Send a message to the Conversation Agent."""
        metrics.inc("chat_requests")
        orchestrator = get_orchestrator()

        with metrics.timer("chat_latency"):
            response = await orchestrator.chat(
                user_id=req.user_id,
                message=req.message,
                session_id=req.session_id,
                enable_prediction=req.enable_prediction,
            )

        logger.info(
            "Chat completed for user %s",
            req.user_id,
            extra={"user_id": req.user_id, "session_id": req.session_id, "operation": "chat"},
        )
        return ChatResponse(
            response=response,
            user_id=req.user_id,
            session_id=req.session_id,
        )

    @router.post("/reflect/{user_id}", response_model=ReflectResponse)
    async def reflect(user_id: str) -> ReflectResponse:
        """Trigger memory consolidation (Reflection Agent) for a user."""
        _validate_user_id(user_id)
        metrics.inc("reflection_requests")
        orchestrator = get_orchestrator()

        with metrics.timer("reflection_latency"):
            summary = await orchestrator.reflect(user_id=user_id)

        logger.info(
            "Reflection completed for user %s",
            user_id,
            extra={"user_id": user_id, "operation": "reflect"},
        )
        return ReflectResponse(summary=summary, user_id=user_id)

    @router.get("/memories/{user_id}", response_model=MemoryListResponse)
    async def list_memories(user_id: str) -> MemoryListResponse:
        """List all memories for a user."""
        _validate_user_id(user_id)
        metrics.inc("memory_list_requests")
        manager = MemoryManager()

        with metrics.timer("memory_list_latency"):
            result = manager.get_all(user_id=user_id)

        memories = [m.model_dump(mode="json") for m in result.results]
        return MemoryListResponse(memories=memories, total=result.total, user_id=user_id)

    @router.delete("/memories/{memory_id}")
    async def delete_memory(memory_id: str) -> DeleteResponse:
        """Delete a single memory (right to be forgotten)."""
        metrics.inc("memory_delete_requests")
        manager = MemoryManager()
        manager.delete(memory_id=memory_id)
        logger.info("Memory deleted: %s", memory_id, extra={"operation": "memory_delete"})
        return DeleteResponse(status="deleted")

    @router.delete("/memories/user/{user_id}")
    async def delete_all_memories(user_id: str) -> DeleteResponse:
        """Delete all memories for a user (right to be forgotten)."""
        _validate_user_id(user_id)
        metrics.inc("memory_delete_all_requests")
        manager = MemoryManager()
        manager.delete_all(user_id=user_id)
        logger.info(
            "All memories deleted for user %s",
            user_id,
            extra={"user_id": user_id, "operation": "memory_delete_all"},
        )
        return DeleteResponse(status="deleted_all")

    return router
