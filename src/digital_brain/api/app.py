"""FastAPI application — HTTP interface for the Digital Brain."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI

from digital_brain.agents.orchestrator import DigitalBrainOrchestrator
from digital_brain.api.routes import create_router
from digital_brain.config import get_settings
from digital_brain.logging_config import setup_logging
from digital_brain.metrics import metrics
from digital_brain.middleware import register_middleware

logger = logging.getLogger(__name__)

_orchestrator: DigitalBrainOrchestrator | None = None
_telegram_channel: Any = None
_telegram_task: asyncio.Task | None = None
_abort_signal: asyncio.Event | None = None


def get_orchestrator() -> DigitalBrainOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = DigitalBrainOrchestrator()
    return _orchestrator


def get_telegram_channel() -> Any:
    """Return the active TelegramChannel instance, or None."""
    return _telegram_channel


def _build_dispatch_fn(orchestrator: DigitalBrainOrchestrator) -> Any:
    """Build the AI dispatch function for the inbound pipeline."""

    async def dispatch(user_id: str, text: str, media_parts: list[Any]) -> str:
        return await orchestrator.chat(user_id=user_id, message=text, media_parts=media_parts)

    return dispatch


async def _handle_command(channel: Any, command: str, args: str, message: Any) -> None:
    """Handle Telegram bot commands."""
    from digital_brain.channels.telegram.send import send_text_message

    chat_id = message.chat_id
    bot = channel.bot
    sender_id = message.sender_id

    if command == "start":
        await send_text_message(
            bot,
            chat_id,
            "Ciao! Sono il tuo Digital Brain. "
            "Puoi parlarmi di qualsiasi cosa e ricorderò le nostre conversazioni.",
        )
    elif command == "help":
        help_text = (
            "**Comandi disponibili:**\n"
            "/start — Avvia il bot\n"
            "/help — Mostra questo messaggio\n"
            "/memories — Mostra le tue memorie\n"
            "/forget — Cancella tutte le memorie\n"
            "/reflect — Avvia la riflessione sulle memorie"
        )
        await send_text_message(bot, chat_id, help_text)
    elif command == "memories":
        from digital_brain.memory.manager import MemoryManager

        mapper = _get_user_mapper()
        brain_id = mapper.resolve(sender_id, message.sender_name)
        manager = MemoryManager()
        result = manager.get_all(user_id=brain_id)
        if result.results:
            lines = [f"**Le tue memorie ({result.total}):**\n"]
            for mem in result.results[:20]:
                text_val = mem.memory if hasattr(mem, "memory") else str(mem)
                lines.append(f"• {text_val}")
            await send_text_message(bot, chat_id, "\n".join(lines))
        else:
            await send_text_message(bot, chat_id, "Non hai ancora nessuna memoria.")
    elif command == "forget":
        from digital_brain.memory.manager import MemoryManager

        mapper = _get_user_mapper()
        brain_id = mapper.resolve(sender_id, message.sender_name)
        manager = MemoryManager()
        manager.delete_all(user_id=brain_id)
        await send_text_message(bot, chat_id, "Tutte le tue memorie sono state cancellate.")
    elif command == "reflect":
        orchestrator = get_orchestrator()
        mapper = _get_user_mapper()
        brain_id = mapper.resolve(sender_id, message.sender_name)
        await send_text_message(bot, chat_id, "Sto riflettendo sulle tue memorie…")
        summary = await orchestrator.reflect(user_id=brain_id)
        await send_text_message(bot, chat_id, summary)
    else:
        await send_text_message(
            bot, chat_id, f"Comando sconosciuto: /{command}. Usa /help per la lista."
        )


def _get_user_mapper() -> Any:
    """Lazy singleton for the Telegram user mapper."""
    global _user_mapper
    if "_user_mapper" not in globals() or _user_mapper is None:
        from digital_brain.channels.telegram.mapping import TelegramUserMapper

        _user_mapper = TelegramUserMapper()
    return _user_mapper


_user_mapper: Any = None


async def _setup_telegram(orchestrator: DigitalBrainOrchestrator) -> None:
    """Set up and start the Telegram channel if enabled."""
    global _telegram_channel, _telegram_task, _abort_signal

    settings = get_settings()
    if not settings.telegram.enabled:
        logger.info("Telegram integration disabled")
        return

    if not settings.telegram.bot_token:
        logger.warning("Telegram enabled but TELEGRAM_BOT_TOKEN not set")
        return

    from digital_brain.channels.debounce import InboundDebouncer
    from digital_brain.channels.media import MediaProcessor
    from digital_brain.channels.pipeline import InboundPipeline
    from digital_brain.channels.security import DmPolicyEnforcer
    from digital_brain.channels.telegram.plugin import TelegramChannel

    # Build pipeline components
    security = DmPolicyEnforcer(
        policy=settings.telegram.dm_policy,
        allow_from=[f"telegram:{uid}" for uid in settings.telegram.allow_from],
    )
    debouncer = InboundDebouncer(debounce_ms=settings.telegram.debounce_ms)
    media_processor = MediaProcessor(
        max_file_size_bytes=settings.media.max_file_size_mb * 1024 * 1024,
        allowed_types=settings.media.allowed_types,
    )

    mapper = _get_user_mapper()

    async def resolve_user_id(channel: str, sender_id: str) -> str:
        return mapper.resolve(sender_id)

    pipeline = InboundPipeline(
        security=security,
        debouncer=debouncer,
        media_processor=media_processor,
        dispatch_fn=_build_dispatch_fn(orchestrator),
        resolve_user_id=resolve_user_id,
    )

    async def on_message(channel: TelegramChannel, message: Any) -> None:
        await pipeline.process(channel, message)

    _telegram_channel = TelegramChannel(
        bot_token=settings.telegram.bot_token,
        webhook_url=settings.telegram.webhook_url,
        webhook_secret=settings.telegram.webhook_secret,
        on_message=on_message,
        on_command=_handle_command,
    )

    _abort_signal = asyncio.Event()

    if settings.telegram.webhook_url:
        # Webhook mode: initialize the bot but don't block
        # The webhook endpoint handles updates
        from telegram.ext import Application

        builder = Application.builder().token(settings.telegram.bot_token)
        _telegram_channel._app = builder.build()
        _telegram_channel._bot = _telegram_channel._app.bot

        bot_info = await _telegram_channel._bot.get_me()
        _telegram_channel._bot_username = bot_info.username or ""

        from telegram.ext import MessageHandler, filters

        _telegram_channel._app.add_handler(
            MessageHandler(filters.ALL, _telegram_channel._handle_update)
        )
        await _telegram_channel._app.initialize()
        await _telegram_channel._app.bot.set_webhook(
            url=settings.telegram.webhook_url,
            secret_token=settings.telegram.webhook_secret or None,
        )
        _telegram_channel._running = True
        logger.info(
            "Telegram webhook mode: @%s -> %s",
            _telegram_channel._bot_username,
            settings.telegram.webhook_url,
        )
    else:
        # Polling mode: run in a background task
        _telegram_task = asyncio.create_task(_telegram_channel.start(_abort_signal))
        logger.info("Telegram polling mode started")


async def _teardown_telegram() -> None:
    """Stop the Telegram channel."""
    global _telegram_channel, _telegram_task, _abort_signal

    if _abort_signal is not None:
        _abort_signal.set()

    if _telegram_task is not None:
        try:
            await asyncio.wait_for(_telegram_task, timeout=5.0)
        except asyncio.TimeoutError:
            _telegram_task.cancel()
        _telegram_task = None

    if _telegram_channel is not None:
        await _telegram_channel.stop()
        _telegram_channel = None

    _abort_signal = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    import os

    settings = get_settings()
    setup_logging(level=settings.logging.level, fmt=settings.logging.format)

    # Google ADK reads GOOGLE_API_KEY from os.environ, but Pydantic Settings
    # only loads .env into its own object.  Bridge the gap.
    if settings.llm.google_api_key and "GOOGLE_API_KEY" not in os.environ:
        os.environ["GOOGLE_API_KEY"] = settings.llm.google_api_key

    logger.info("Digital Brain v0.1.0 starting up…")
    orchestrator = get_orchestrator()

    # Start Telegram if enabled
    await _setup_telegram(orchestrator)

    yield

    # Shutdown Telegram
    await _teardown_telegram()
    logger.info("Digital Brain shutting down…")


app = FastAPI(
    title="Digital Brain",
    description="Cognitive architecture for AI agents with persistent memory",
    version="0.1.0",
    lifespan=lifespan,
)

register_middleware(app)
app.include_router(create_router(get_orchestrator))

# Telegram webhook endpoint (always registered; returns 503 if channel not started)
from digital_brain.api.webhooks import create_webhook_router  # noqa: E402

app.include_router(
    create_webhook_router(
        get_telegram_channel=get_telegram_channel,
        webhook_secret=get_settings().telegram.webhook_secret,
    )
)


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
