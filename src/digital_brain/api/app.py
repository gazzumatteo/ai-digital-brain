"""FastAPI application — HTTP interface for the Digital Brain."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from digital_brain.agents.orchestrator import DigitalBrainOrchestrator
from digital_brain.api.routes import create_router

logger = logging.getLogger(__name__)

_orchestrator: DigitalBrainOrchestrator | None = None


def get_orchestrator() -> DigitalBrainOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = DigitalBrainOrchestrator()
    return _orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Digital Brain starting up…")
    get_orchestrator()
    yield
    logger.info("Digital Brain shutting down…")


app = FastAPI(
    title="Digital Brain",
    description="Cognitive architecture for AI agents with persistent memory",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(create_router(get_orchestrator))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
