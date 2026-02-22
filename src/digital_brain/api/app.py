"""FastAPI application — HTTP interface for the Digital Brain."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from digital_brain.agents.orchestrator import DigitalBrainOrchestrator
from digital_brain.api.routes import create_router
from digital_brain.config import get_settings
from digital_brain.logging_config import setup_logging
from digital_brain.metrics import metrics
from digital_brain.middleware import register_middleware

logger = logging.getLogger(__name__)

_orchestrator: DigitalBrainOrchestrator | None = None


def get_orchestrator() -> DigitalBrainOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = DigitalBrainOrchestrator()
    return _orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(level=settings.logging.level, fmt=settings.logging.format)
    logger.info("Digital Brain v0.1.0 starting up…")
    get_orchestrator()
    yield
    logger.info("Digital Brain shutting down…")


app = FastAPI(
    title="Digital Brain",
    description="Cognitive architecture for AI agents with persistent memory",
    version="0.1.0",
    lifespan=lifespan,
)

register_middleware(app)
app.include_router(create_router(get_orchestrator))


@app.get("/health")
async def health() -> dict:
    """Health check with component status and metrics summary."""
    settings = get_settings()

    components: dict[str, str] = {}

    # Qdrant connectivity
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(host=settings.qdrant.host, port=settings.qdrant.port, timeout=3)
        client.get_collections()
        components["qdrant"] = "healthy"
    except Exception:
        components["qdrant"] = "unreachable"

    # Neo4j (only if enabled)
    if settings.neo4j.enabled:
        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(
                settings.neo4j.url,
                auth=(settings.neo4j.username, settings.neo4j.password),
            )
            driver.verify_connectivity()
            driver.close()
            components["neo4j"] = "healthy"
        except Exception:
            components["neo4j"] = "unreachable"

    all_healthy = all(v == "healthy" for v in components.values())

    return {
        "status": "ok" if all_healthy else "degraded",
        "version": "0.1.0",
        "components": components,
        "config": {
            "llm_provider": settings.llm.provider,
            "llm_model": settings.llm.model,
            "embedder_provider": settings.embedder.provider,
        },
        "metrics": metrics.snapshot(),
    }
