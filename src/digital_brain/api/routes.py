"""API routes for the Digital Brain."""

from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from digital_brain.agents.orchestrator import DigitalBrainOrchestrator
from digital_brain.memory.manager import MemoryManager


# --- Request / Response models ---


class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: str | None = None
    enable_prediction: bool = Field(default=True)


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
        orchestrator = get_orchestrator()
        response = await orchestrator.chat(
            user_id=req.user_id,
            message=req.message,
            session_id=req.session_id,
            enable_prediction=req.enable_prediction,
        )
        return ChatResponse(
            response=response,
            user_id=req.user_id,
            session_id=req.session_id,
        )

    @router.post("/reflect/{user_id}", response_model=ReflectResponse)
    async def reflect(user_id: str) -> ReflectResponse:
        """Trigger memory consolidation (Reflection Agent) for a user."""
        orchestrator = get_orchestrator()
        summary = await orchestrator.reflect(user_id=user_id)
        return ReflectResponse(summary=summary, user_id=user_id)

    @router.get("/memories/{user_id}", response_model=MemoryListResponse)
    async def list_memories(user_id: str) -> MemoryListResponse:
        """List all memories for a user."""
        manager = MemoryManager()
        result = manager.get_all(user_id=user_id)
        memories = [m.model_dump(mode="json") for m in result.results]
        return MemoryListResponse(memories=memories, total=result.total, user_id=user_id)

    @router.delete("/memories/{memory_id}")
    async def delete_memory(memory_id: str) -> DeleteResponse:
        """Delete a single memory (right to be forgotten)."""
        manager = MemoryManager()
        manager.delete(memory_id=memory_id)
        return DeleteResponse(status="deleted")

    @router.delete("/memories/user/{user_id}")
    async def delete_all_memories(user_id: str) -> DeleteResponse:
        """Delete all memories for a user (right to be forgotten)."""
        manager = MemoryManager()
        manager.delete_all(user_id=user_id)
        return DeleteResponse(status="deleted_all")

    return router
