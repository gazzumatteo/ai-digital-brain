# Digital Brain — Development Plan

## Project Overview

Implementation of a **Digital Brain** based on the principles of Predictive Coding, Active Inference, and consolidation during "digital sleep", as described in the article series *"From Predictive Coding to Digital Brain"*.

**Technology stack:**
- **Language**: Python 3.11+
- **Agent Framework**: Google ADK (Agent Development Kit)
- **Memory Layer**: Mem0 (Apache 2.0)
- **Vector Store**: Qdrant (self-hosted)
- **Graph Store**: Neo4j (optional)
- **Local LLM**: Ollama
- **Cloud LLM**: Google Gemini (default for ADK), configurable
- **Scheduling**: APScheduler
- **Infrastructure**: Docker Compose

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       DIGITAL BRAIN                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌────────────────────────────────────────────────────┐     │
│   │               CHANNEL LAYER                        │     │
│   │            (Telegram, Future...)                   │     │
│   │                                                    │     │
│   │  ┌──────────┐  ┌──────────────┐                    │     │
│   │  │ Telegram │  │  Future ...  │                    │     │
│   │  │   Bot    │  │  (Discord,   │                    │     │
│   │  │   API    │  │   Slack...)  │                    │     │
│   │  └────┬─────┘  └──────┬───────┘                    │     │
│   │       └───────────────┘                            │     │
│   │                      │                             │     │
│   │         ┌────────────▼────────────┐                │     │
│   │         │   Inbound Pipeline      │                │     │
│   │         │  normalize → debounce   │                │     │
│   │         │  → security → dispatch  │                │     │
│   │         └────────────┬────────────┘                │     │
│   └──────────────────────┼─────────────────────────────┘     │
│                          │                                   │
│   ┌──────────────────────▼─────────────────────────────┐     │
│   │              GOOGLE ADK AGENT LAYER                │     │
│   │                                                    │     │
│   │  ┌──────────────┐  ┌─────────────┐  ┌──────────┐  │     │
│   │  │ Conversation │  │ Reflection  │  │Predictive│  │     │
│   │  │    Agent     │  │   Agent     │  │  Agent   │  │     │
│   │  └──────┬───────┘  └──────┬──────┘  └────┬─────┘  │     │
│   └─────────┼─────────────────┼───────────────┼────────┘     │
│             │                 │               │              │
│   ┌─────────▼─────────────────▼───────────────▼────────┐     │
│   │                   MEMORY LAYER                     │     │
│   │                     (Mem0)                         │     │
│   │    ┌─────────┐  ┌──────────┐  ┌────────────┐      │     │
│   │    │ Vector  │  │  Graph   │  │ Key-Value  │      │     │
│   │    │ (Qdrant)│  │ (Neo4j)  │  │  (Redis)   │      │     │
│   │    └─────────┘  └──────────┘  └────────────┘      │     │
│   └────────────────────────────────────────────────────┘     │
│                           │                                  │
│   ┌───────────────────────▼────────────────────────────┐     │
│   │                   LLM LAYER                        │     │
│   │        (Ollama / Gemini / configurable)            │     │
│   └────────────────────────────────────────────────────┘     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
ai-digital-brain/
├── docker-compose.yml              # Full infrastructure
├── Dockerfile                      # Application image
├── pyproject.toml                  # Dependencies and metadata (uv/pip)
├── .env.example                    # Environment variables template
├── .gitignore
├── README.md
│
├── src/
│   └── digital_brain/
│       ├── __init__.py
│       ├── config.py               # Centralized configuration (Pydantic Settings)
│       │
│       ├── memory/                 # Memory layer (Mem0 wrapper)
│       │   ├── __init__.py
│       │   ├── manager.py          # MemoryManager: Mem0 init and config
│       │   ├── tools.py            # ADK Tools: memory_store, memory_search, memory_get
│       │   └── schemas.py          # Pydantic models for memory entities
│       │
│       ├── agents/                 # Google ADK Agents
│       │   ├── __init__.py
│       │   ├── conversation.py     # ConversationAgent: memory-augmented dialogue
│       │   ├── reflection.py       # ReflectionAgent: consolidation ("digital sleep")
│       │   ├── predictive.py       # PredictiveAgent: proactive pre-loading
│       │   └── orchestrator.py     # Main orchestrator
│       │
│       ├── channels/               # Multi-channel messaging layer (Phase 6+)
│       │   ├── __init__.py
│       │   ├── base.py             # ChannelPlugin ABC + InboundMessage/OutboundResult
│       │   ├── registry.py         # ChannelRegistry: active channels registry
│       │   ├── pipeline.py         # Inbound pipeline: normalize → dispatch
│       │   ├── media.py            # MediaProcessor: download, validation, ADK Part conversion
│       │   ├── debounce.py         # Rapid consecutive message debouncer
│       │   ├── chunking.py         # Text/markdown chunking for long responses
│       │   ├── security.py         # DM policy, pairing, allowlist
│       │   │
│       │   └── telegram/           # Telegram Bot API integration (Phase 7)
│       │       ├── __init__.py
│       │       ├── plugin.py       # TelegramChannel(ChannelPlugin)
│       │       ├── handlers.py     # Inbound: text, media, commands, groups
│       │       ├── send.py         # Outbound: message/media sending
│       │       └── mapping.py      # Telegram user_id → brain user_id
│       │
│       ├── tools/                  # Custom ADK Tools
│       │   ├── __init__.py
│       │   ├── calendar_tool.py    # (optional) Calendar integration
│       │   └── context_tool.py     # Context signals (time, session, patterns)
│       │
│       ├── scheduler/              # Scheduling for Reflection Agent
│       │   ├── __init__.py
│       │   └── jobs.py             # Job definitions (APScheduler)
│       │
│       └── api/                    # HTTP interface (FastAPI)
│           ├── __init__.py
│           ├── app.py              # FastAPI app (or ADK dev server wrapper)
│           ├── routes.py           # Endpoints: /chat, /memories, /reflect
│           └── webhooks.py         # Webhook endpoint: /webhooks/telegram
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Fixtures: mock Mem0, mock LLM
│   ├── test_memory_manager.py
│   ├── test_conversation_agent.py
│   ├── test_reflection_agent.py
│   ├── test_predictive_agent.py
│   └── test_integration.py         # End-to-end tests with real services
│
└── scripts/
    ├── seed_memories.py            # Seed initial memories for demo
    └── run_reflection.py           # Manual trigger for Reflection Agent
```

---

## Development Phases

### Phase 1 — Foundations (Infrastructure + Memory Layer)

**Goal**: Working stack with Mem0 configured and testable.

#### 1.1 Project Setup
- [ ] Create `pyproject.toml` with dependencies:
  - `google-adk`
  - `mem0ai`
  - `fastapi`, `uvicorn`
  - `pydantic-settings`
  - `apscheduler`
  - `pytest`, `pytest-asyncio`
- [ ] Create `.env.example` with all required variables
- [ ] Create `.gitignore` (Python, .env, __pycache__, .venv, etc.)
- [ ] Create multi-stage `Dockerfile` (builder + runtime)
- [ ] Create `docker-compose.yml` with services:
  - `qdrant` (vector store)
  - `neo4j` (graph store, optional)
  - `ollama` (local LLM)
  - `app` (digital brain)

#### 1.2 Centralized Configuration
- [ ] `config.py` with Pydantic `BaseSettings`:
  - LLM provider (ollama/gemini/openai) + model name
  - Mem0 config (vector store, graph store, embedder)
  - Consolidation parameters (schedule, threshold, TTL)
  - Scoping defaults (user_id, agent_id)

#### 1.3 Memory Manager (Mem0 wrapper)
- [ ] `memory/manager.py` — `MemoryManager` class:
  - `__init__`: initialize Mem0 with config for Qdrant + Neo4j + Ollama embeddings
  - `add(messages, user_id, metadata)`: wrapper on `memory.add()`
  - `search(query, user_id, limit)`: wrapper on `memory.search()`
  - `get_all(user_id)`: all memories for a user
  - `delete(memory_id)`: delete a single memory
  - `get_recent(user_id, hours)`: memories from the last N hours
- [ ] `memory/schemas.py` — Pydantic models:
  - `MemoryEntry`: id, content, user_id, created_at, metadata, score
  - `MemorySearchResult`: list of MemoryEntry with score
- [ ] Unit tests with Mem0 mock

#### 1.4 Memory Tools for ADK
- [ ] `memory/tools.py` — functions to expose as ADK FunctionTool:
  ```python
  def memory_store(content: str, user_id: str, metadata: dict = None) -> str:
      """Save information to long-term memory."""

  def memory_search(query: str, user_id: str, limit: int = 5) -> list[dict]:
      """Search for memories relevant to the query."""

  def memory_get_all(user_id: str) -> list[dict]:
      """Retrieve all memories for a user."""
  ```

**Deliverable**: `docker compose up` starts Qdrant + Ollama, tests pass.

---

### Phase 2 — Conversation Agent (Base Mnemonic Loop)

**Goal**: Working conversational agent with persistent memory.

#### 2.1 Conversation Agent with Google ADK
- [ ] `agents/conversation.py` — `create_conversation_agent()`:
  ```python
  from google.adk.agents import LlmAgent
  from google.adk.tools import FunctionTool

  conversation_agent = LlmAgent(
      name="conversation_agent",
      model="gemini-2.0-flash",  # or ollama via LiteLLM
      instruction="""You are a personal assistant with persistent memory.
      Before responding, always search memory for relevant information.
      After the conversation, save important facts to memory.""",
      tools=[
          FunctionTool(memory_search),
          FunctionTool(memory_store),
      ],
  )
  ```
- [ ] System prompt with instructions for:
  - Search memory **before** responding (retrieval)
  - Extract facts, preferences, entities from conversation (extraction)
  - Save new facts to memory (storage)
- [ ] `session_id` and `user_id` management via ADK Session/State

#### 2.2 HTTP API
- [ ] `api/app.py` — FastAPI with endpoints:
  - `POST /chat` — input: user message + user_id, output: agent response
  - `GET /memories/{user_id}` — list memories
  - `DELETE /memories/{memory_id}` — delete memory (right to be forgotten)
- [ ] Integration with ADK Runner for agent execution:
  ```python
  from google.adk.runners import Runner
  from google.adk.sessions import InMemorySessionService

  runner = Runner(
      agent=conversation_agent,
      app_name="digital_brain",
      session_service=InMemorySessionService(),
  )
  ```

#### 2.3 End-to-end Tests
- [ ] Test: send message → agent responds → memory saved
- [ ] Test: send second message → agent retrieves previous memory
- [ ] Test: verify memories persist across different sessions

**Deliverable**: Working chat that remembers across sessions. `POST /chat` → response with memorized context.

---

### Phase 3 — Reflection Agent ("Digital Sleep")

**Goal**: Automatic memory consolidation.

#### 3.1 Reflection Agent
- [ ] `agents/reflection.py` — `create_reflection_agent()`:
  ```python
  reflection_agent = LlmAgent(
      name="reflection_agent",
      model="gemini-2.0-flash",
      instruction="""You are a memory consolidation agent.
      Analyze recent memories and:
      1. Identify recurring patterns
      2. Find and resolve contradictions
      3. Synthesize high-level insights
      4. Mark outdated memories as obsolete""",
      tools=[
          FunctionTool(memory_get_all),
          FunctionTool(memory_search),
          FunctionTool(memory_store),
          FunctionTool(memory_delete),
      ],
  )
  ```
- [ ] Consolidation logic:
  - **GATHER**: retrieve memories from the last 24h
  - **ANALYZE**: LLM identifies patterns, conflicts, redundancies
  - **SYNTHESIZE**: create higher-level synthetic memories (episodic → semantic)
  - **PRUNE**: archive/delete obsolete or duplicate memories
- [ ] Memory metadata:
  - `memory_type`: `episodic` | `semantic` | `insight`
  - `confidence`: 0.0-1.0
  - `source_count`: how many episodic memories support an insight
  - `ttl`: optional time-to-live

#### 3.2 Scheduling
- [ ] `scheduler/jobs.py` — APScheduler configuration:
  ```python
  scheduler.add_job(
      run_reflection,
      trigger="cron",
      hour=3,  # "digital sleep" at 03:00
      minute=0,
  )
  ```
- [ ] Manual endpoint: `POST /reflect/{user_id}` for on-demand trigger
- [ ] Detailed logging: how many memories analyzed, consolidated, deleted

#### 3.3 Safeguards
- [ ] Minimum occurrence threshold before synthesizing (avoid false patterns)
- [ ] Maintain links between synthetic memories and episodic sources
- [ ] TTL on consolidated memories with recency weighting
- [ ] Test: verify duplicate memories get merged
- [ ] Test: verify contradictions get resolved (newer wins)

**Deliverable**: Reflection Agent runnable via cron or manually. Memories get consolidated.

---

### Phase 4 — Predictive Engine (Active Inference)

**Goal**: Proactive context-based memory pre-loading.

#### 4.1 Context Signals
- [ ] `tools/context_tool.py` — signal collection:
  ```python
  def get_context_signals(user_id: str) -> dict:
      """Return contextual signals for prediction."""
      return {
          "time_of_day": "morning|afternoon|evening",
          "day_of_week": "monday|...|sunday",
          "recent_topics": [...],         # recent session topics
          "session_count_today": 3,
          "last_session_gap_hours": 14.5,
      }
  ```

#### 4.2 Predictive Agent
- [ ] `agents/predictive.py` — `create_predictive_agent()`:
  ```python
  predictive_agent = LlmAgent(
      name="predictive_agent",
      model="gemini-2.0-flash",
      instruction="""Based on context signals and recent memories,
      predict what information the user will likely need.
      Return a list of search queries to pre-load.""",
      tools=[
          FunctionTool(get_context_signals),
          FunctionTool(memory_search),
      ],
  )
  ```
- [ ] Pre-loading flow:
  1. User starts session → collect context signals
  2. Predictive Agent generates predictive queries
  3. Pre-fetch relevant memories
  4. Inject as "background knowledge" into the Conversation Agent context
- [ ] Confidence threshold: pre-fetch only if confidence > 0.7

#### 4.3 Integration with Conversation Agent
- [ ] `agents/orchestrator.py` — full orchestration:
  ```python
  async def handle_session_start(user_id: str, session_id: str):
      # 1. Predictive pre-loading
      predictions = await run_predictive_agent(user_id)
      # 2. Pre-fetch memories
      preloaded = await prefetch_memories(predictions)
      # 3. Inject into conversation context
      return create_augmented_session(preloaded)
  ```
- [ ] Feedback loop: track whether predictions were useful (did the user actually ask about those topics?)

#### 4.4 Safeguards
- [ ] Cache TTL on predictions (invalidate on topic change)
- [ ] Maximum token budget for pre-loading
- [ ] Do not announce predictions to the user (avoid "creepy factor")
- [ ] Test: verify predictions are relevant to context

**Deliverable**: The agent anticipates user needs by pre-loading relevant memories.

---

### Phase 5 — Hardening and Production

**Goal**: Robust, documented system ready for open-source release.

#### 5.1 Privacy and Security
- [x] `DELETE /memories/user/{user_id}` endpoint — complete "right to be forgotten"
- [x] Strict scoping: no memory leaks between different users
  - `user_id` validation with regex (alphanumeric, 1-128 chars)
  - Rejection of path-traversal, injection, and special characters
  - Validation at Pydantic model and route level
- [x] No sensitive content logging (sanitize before logging)
  - `logging_config.py` module with pattern matching for API keys (Google, OpenAI, GitHub), passwords, tokens
  - Automatic sanitization on JSONFormatter and SanitizedTextFormatter
- [x] Rate limiting on API endpoints
  - `RateLimitMiddleware` with sliding window per IP
  - Configurable via `RATE_LIMIT_ENABLED` and `RATE_LIMIT_REQUESTS_PER_MINUTE`

#### 5.2 Observability
- [x] Structured logging (JSON) with correlation ID per session
  - `CorrelationIDMiddleware` generates/propagates `X-Correlation-ID` on every request
  - `JSONFormatter` emits logs as single-line JSON with timestamp, level, correlation_id, extra fields
  - `SanitizedTextFormatter` for text mode with redaction
  - Configurable via `LOG_LEVEL` and `LOG_FORMAT` (json/text)
- [x] Metrics:
  - Thread-safe `MetricsCollector` with counters and timers
  - Tracking: chat_requests, reflection_requests, memory ops, rate_limited
  - Timers: chat_latency, reflection_latency, prediction_latency, conversation_latency, http_request
  - HTTP status code counters (http_200, http_429, etc.)
- [x] Health check endpoint: `/health`
  - Verifies Qdrant and Neo4j connectivity (if enabled)
  - Status: "ok" or "degraded"
  - Exposes active config (provider, model) and metrics snapshot

#### 5.3 Configurability
- [x] Multi-provider LLM support (Ollama, Gemini, OpenAI) via config
- [x] Tuning parameters exposed as environment variables:
  - `REFLECTION_SCHEDULE_HOUR`, `REFLECTION_SCHEDULE_MINUTE`
  - `PREDICTION_CONFIDENCE_THRESHOLD`
  - `MEMORY_TTL_DAYS`
  - `MAX_PRELOAD_TOKENS`
  - `LOG_LEVEL`, `LOG_FORMAT`
  - `RATE_LIMIT_ENABLED`, `RATE_LIMIT_REQUESTS_PER_MINUTE`
- [x] Docker Compose profiles: `local` (Ollama), `graph` (Neo4j)

#### 5.4 Documentation and Release
- [x] README.md with:
  - Quick start (4 commands to get running)
  - ASCII architecture diagram
  - Agent table with roles
  - Complete API reference with request/response examples
  - Configuration tables for each section
  - Docker and development instructions
- [x] `scripts/seed_memories.py` script for demo
- [x] CI with GitHub Actions (lint, test, coverage)
- [ ] Tag v0.1.0 and release

**Deliverable**: Complete, forkable open-source repository with documentation.

---

### Phase 6 — Channel Architecture (Multi-Channel Infrastructure)

**Goal**: Create the abstraction that allows the Digital Brain to communicate on any channel (Telegram and future ones) through a unified interface.

> *Pattern inspired by OpenClaw: `ChannelPlugin` interface — the only abstraction that matters. Every channel-specific detail (message format, API, authentication, target format) is encapsulated behind a common contract. The AI layer does not and should not know whether a message comes from Telegram or WhatsApp.*

#### 6.1 Channel Plugin Interface (ABC)
- [x] `channels/base.py` — Abstract Base Class `ChannelPlugin`:
  ```python
  from abc import ABC, abstractmethod
  from dataclasses import dataclass
  from typing import Optional
  import asyncio

  @dataclass
  class MediaAttachment:
      type: str               # "image" | "audio" | "video" | "document" | "voice" | "sticker"
      mime_type: str           # "image/jpeg", "audio/ogg", "application/pdf", ...
      file_id: str             # File ID in the source channel (e.g. Telegram file_id)
      file_size: int | None = None
      filename: str | None = None
      duration_seconds: float | None = None   # For audio/video
      width: int | None = None                # For images/video
      height: int | None = None               # For images/video
      caption: str | None = None              # Optional media caption

  @dataclass
  class InboundMessage:
      channel: str            # "telegram" | future channels
      chat_id: str            # Unique chat ID
      sender_id: str          # Sender ID
      sender_name: str        # Display name
      text: str               # Message text (or caption if media only)
      media: list[MediaAttachment]  # Attached media (images, audio, video, documents)
      reply_to_id: Optional[str] = None
      thread_id: Optional[str] = None
      raw: dict = None        # Original channel payload

  @dataclass
  class OutboundResult:
      channel: str
      message_id: str
      success: bool
      error: Optional[str] = None

  class ChannelPlugin(ABC):
      @abstractmethod
      def channel_id(self) -> str: ...

      @abstractmethod
      def capabilities(self) -> dict: ...

      @abstractmethod
      async def start(self, abort_signal: asyncio.Event) -> None:
          """Start message reception (webhook, polling, WS)."""

      @abstractmethod
      async def stop(self) -> None:
          """Graceful shutdown."""

      @abstractmethod
      async def send_text(self, to: str, text: str, **kwargs) -> OutboundResult: ...

      @abstractmethod
      async def send_media(self, to: str, text: str, media_url: str, **kwargs) -> OutboundResult: ...

      @abstractmethod
      async def health_check(self) -> dict: ...

      @abstractmethod
      def normalize_target(self, raw: str) -> Optional[str]: ...
  ```

#### 6.2 Channel Registry
- [x] `channels/registry.py` — Active channels registry:
  ```python
  class ChannelRegistry:
      def register(self, plugin: ChannelPlugin) -> None: ...
      def get(self, channel_id: str) -> ChannelPlugin: ...
      def list_channels(self) -> list[str]: ...
      async def start_all(self, abort: asyncio.Event) -> None: ...
      async def stop_all(self) -> None: ...
      async def health_check_all(self) -> dict[str, dict]: ...
  ```

#### 6.3 Inbound Pipeline (inspired by OpenClaw)
- [x] `channels/pipeline.py` — Inbound message processing pipeline:
  1. **Normalize**: convert raw channel event → standard `InboundMessage`
  2. **Security check**: verify pairing/allowlist
  3. **Debounce**: coalesce rapid consecutive messages from the same user
  4. **Resolve session**: map `(channel, chat_id)` → `(user_id, session_key)`
  5. **Resolve media**: download binary files via channel → `bytes`, build multimodal `types.Part` for ADK
  6. **Dispatch to AI**: build `types.Content(parts=[text_part, *media_parts])` and forward to Conversation Agent
  7. **Send response**: AI response → source channel via `send_text()` or `send_media()`

#### 6.3.1 Media Processing
- [x] `channels/media.py` — Media handling in pipeline:
  ```python
  class MediaProcessor:
      """Download media from channel and convert to types.Part for Google ADK."""

      async def download(self, channel: ChannelPlugin, attachment: MediaAttachment) -> bytes:
          """Download binary file from the source channel."""

      def to_adk_part(self, data: bytes, mime_type: str) -> types.Part:
          """Convert bytes + mime_type to a types.Part for multimodal Gemini."""
          # Gemini accepts: image/*, audio/*, video/*, application/pdf
          return types.Part.from_bytes(data=data, mime_type=mime_type)

      async def process_attachments(
          self, channel: ChannelPlugin, attachments: list[MediaAttachment]
      ) -> list[types.Part]:
          """Full pipeline: download → validation → ADK Parts conversion."""
  ```
- [x] Validation: maximum file size (configurable, default 20MB)
- [x] MIME type allowlist (prevents executables, malicious archives)
- [x] Types supported by the multimodal LLM:
  - **Images**: `image/jpeg`, `image/png`, `image/webp`, `image/gif` → passed directly to Gemini
  - **Audio**: `audio/ogg`, `audio/mpeg`, `audio/wav` → passed to Gemini (native support)
  - **Video**: `video/mp4`, `video/webm` → passed to Gemini (native support)
  - **Documents**: `application/pdf` → passed to Gemini; other formats → text extraction if possible

#### 6.4 Inbound Debouncer (pattern from OpenClaw)
- [x] `channels/debounce.py` — Coalesce rapid messages:
  ```python
  class InboundDebouncer:
      """Prevents 5 AI responses for 5 rapid consecutive messages.
      Waits debounce_ms after the last message, then flushes all as one."""

      def __init__(self, debounce_ms: int = 1500, on_flush: Callable): ...
      async def enqueue(self, key: str, message: InboundMessage) -> None: ...
  ```

#### 6.5 Security — DM Policy & Pairing (pattern from OpenClaw)
- [x] `channels/security.py` — Access control:
  ```python
  class DmPolicyEnforcer:
      """Three modes: 'open' (everyone), 'pairing' (allowlist + approval), 'disabled'."""
      def check_access(self, channel: str, sender_id: str) -> tuple[bool, str]: ...
      def approve(self, channel: str, sender_id: str) -> None: ...
  ```

#### 6.6 Outbound Chunking
- [x] `channels/chunking.py` — Split long responses:
  - Mode `markdown`: split preserving code blocks, lists, headings (Telegram, 4096 char limit)
  - Mode `text`: greedy length-based split (for future channels without markdown support)

#### 6.7 Channel Configuration
- [x] Extension of `config.py` with channels section:
  ```python
  # Telegram
  TELEGRAM_ENABLED: bool = False
  TELEGRAM_BOT_TOKEN: str = ""
  TELEGRAM_WEBHOOK_URL: str = ""    # If empty → polling mode
  TELEGRAM_WEBHOOK_SECRET: str = ""
  TELEGRAM_DM_POLICY: str = "pairing"  # open | pairing | disabled
  TELEGRAM_ALLOW_FROM: list[str] = []
  TELEGRAM_DEBOUNCE_MS: int = 1500

  # Media processing
  MEDIA_MAX_FILE_SIZE_MB: int = 20        # Maximum accepted file size
  MEDIA_ALLOWED_TYPES: list[str] = [      # Allowed MIME types
      "image/*", "audio/*", "video/*", "application/pdf"
  ]
  ```

#### 6.8 Tests
- [x] Unit tests for ChannelPlugin ABC
- [x] Tests for InboundDebouncer
- [x] Tests for DmPolicyEnforcer
- [x] Tests for text/markdown chunking
- [x] Tests for ChannelRegistry lifecycle
- [x] Tests for MediaProcessor (download, MIME validation, ADK Part conversion)
- [x] Tests for rejecting oversized files / disallowed MIME types

**Deliverable**: Complete and tested multi-channel infrastructure with multimodal media support. No concrete channels yet, but the framework is ready to accommodate them.

---

### Phase 7 — Telegram Integration

**Goal**: Working Telegram bot that allows chatting with the Digital Brain via Telegram.

> *Chosen library: `python-telegram-bot` (mature, async-native, excellent documentation). Alternative: `aiogram` (lighter, FastAPI-friendly). Final decision during implementation.*

#### 7.1 Telegram Plugin
- [x] `channels/telegram/plugin.py` — `TelegramChannel(ChannelPlugin)`:
  - `channel_id()` → `"telegram"`
  - `capabilities()` → `{ chat_types: [direct, group], reactions: True, threads: True, media: True, commands: True }`
  - `start()` → start webhook or polling based on config
  - `send_text()` → send message via Bot API, with markdown parsing
  - `send_media()` → send photos/videos/documents
  - `health_check()` → call `getMe()` and verify connectivity

#### 7.2 Webhook Endpoint (FastAPI)
- [x] `api/webhooks.py` — webhook endpoint:
  ```python
  @router.post("/webhooks/telegram")
  async def telegram_webhook(request: Request):
      """Receive updates from Telegram Bot API."""
      # 1. Validate secret token (header X-Telegram-Bot-Api-Secret-Token)
      # 2. Parse Update
      # 3. Normalize → InboundMessage
      # 4. Pass to pipeline
  ```
- [x] Polling mode support (fallback for local development without tunnel)

#### 7.3 Inbound Handlers (pattern from OpenClaw)
- [x] `channels/telegram/handlers.py`:
  - **Text messages**: normalize, debounce, dispatch
  - **Photo/Image**: extract `file_id` from highest resolution, build `MediaAttachment(type="image")`
  - **Audio/Voice**: extract `file_id`, duration, MIME; voice notes → `type="voice"`, audio files → `type="audio"`
  - **Video/Video note**: extract `file_id`, duration, dimensions; video notes (circular) → `type="video"`
  - **Documents**: extract `file_id`, `file_name`, `mime_type`; supports PDF, spreadsheets, text
  - **Media group buffering**: when user sends an album (multiple photos/videos together), Telegram delivers them as separate updates with the same `media_group_id`. Buffer and flush as a single `InboundMessage` with `media: list[MediaAttachment]`
  - **Caption handling**: if media has a caption, use it as message `text`; if absent, `text = ""`
  - **Text fragment reassembly**: reassemble long messages split by Telegram (>4096 chars)
  - **Group messages**: mention gating — respond only if the bot is mentioned (@botname)
  - **Commands**: `/start` (welcome), `/help`, `/forget` (delete memories)
  - **Sticker**: extract `file_id` + associated emoji, build `MediaAttachment(type="sticker")`

#### 7.4 Outbound — Sending Responses
- [x] `channels/telegram/send.py`:
  - Markdown-aware chunking (preserves code blocks, lists)
  - Limit: 4096 characters per message
  - `reply_to_message_id` support for contextual replies
  - Forum topics support (`message_thread_id`)
  - Rate limiting (30 msg/sec global, 1 msg/sec per chat, Bot API limits)

#### 7.5 Native Telegram Commands
- [x] `/start` — Welcome message + user registration
- [x] `/help` — List available commands
- [x] `/forget` — Delete all memories (right to be forgotten)
- [x] `/memories` — Show a summary of saved memories
- [x] `/reflect` — Manual trigger of the Reflection Agent

#### 7.6 User ID Mapping
- [x] `channels/telegram/mapping.py`:
  - Map `telegram_user_id` → `digital_brain_user_id`
  - First interaction: automatically create the mapping
  - Username/alias support

#### 7.7 Tests
- [x] Test webhook handler with mock Update
- [x] Test message sending with mock Bot API
- [x] Test media group buffering (multi-photo album)
- [x] Test single image reception → correct MediaAttachment
- [x] Test audio/voice reception → MediaAttachment with duration
- [x] Test document reception (PDF) → MediaAttachment with filename and MIME
- [x] Test video reception → MediaAttachment with dimensions and duration
- [x] Test caption handling (media with/without caption)
- [x] Test mention gating in groups
- [x] Test native commands
- [ ] E2e test: Telegram photo → AI describes image → memory saved
- [ ] E2e test: voice note → AI interprets audio → text response

**Deliverable**: Working Telegram bot with multimodal support. Text, images, audio, video, and documents are all processed by the AI. Testable locally with polling.

---

### Phase 8 — Hardening & Telegram UX

**Goal**: Monitoring, optimized UX, and proactive outreach on Telegram.

#### 8.1 Monitoring & Observability
- [ ] Telegram metrics:
  - `telegram_messages_in`, `telegram_messages_out`
  - `telegram_latency_ms`
  - `telegram_errors`
- [ ] Extended health check: `/health` includes Telegram channel status
- [ ] Status dashboard: JSON endpoint with real-time bot status

#### 8.2 Telegram UX Optimizations
- [ ] **Typing indicator**: show "typing..." while AI generates (`sendChatAction`)
- [ ] **Progressive responses**: edit-in-place of message during LLM streaming
- [ ] **Contextual replies**: reply-to on the user's original message
- [ ] **Markdown formatting**: fully leverage Telegram's markdown support
- [ ] **Graceful error handling**: if AI fails, send an apology message to the user

#### 8.3 Proactive Outreach (Digital Brain → User)
- [ ] The Predictive Agent can decide to proactively contact the user:
  - "Good morning! You have the project meeting today at 10"
  - "I noticed we haven't checked in on the diet for 3 days"
- [ ] Respect time windows (do not disturb at night)
- [ ] Configurable preferred channel (Telegram only for now)

#### 8.4 Tests
- [ ] Test: typing indicator works
- [ ] Test: progressive responses (edit-in-place)
- [ ] Test: proactive outreach with mock scheduler
- [ ] E2e test: Telegram message → response with memory → metrics updated

**Deliverable**: Telegram bot with optimized UX, complete monitoring, and proactive capabilities.

---

## Main Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `google-adk` | latest | Agent framework |
| `mem0ai` | latest | Memory layer |
| `fastapi` | ^0.115 | HTTP API |
| `uvicorn` | ^0.34 | ASGI server |
| `pydantic-settings` | ^2.0 | Configuration |
| `apscheduler` | ^3.10 | Scheduling |
| `qdrant-client` | latest | Vector store client |
| `neo4j` | latest | Graph store client (optional) |
| `litellm` | latest | Multi-provider LLM proxy (optional) |
| `python-telegram-bot` | ^21.0 | Telegram Bot API (Phase 7) |
| `pytest` | ^8.0 | Testing |
| `pytest-asyncio` | latest | Async testing |

---

## Docker Compose — Services

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes: [qdrant_data:/qdrant/storage]

  neo4j:
    image: neo4j:5
    ports: ["7474:7474", "7687:7687"]
    environment:
      NEO4J_AUTH: neo4j/password
    profiles: ["graph"]  # optional

  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes: [ollama_data:/root/.ollama]
    profiles: ["local"]  # local LLM only

  app:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [qdrant]
```

---

## Priority and Implementation Order

```
Phase 1 (Foundations)       ████████████████████  Completed
Phase 2 (Conversation)     ████████████████████  Completed
Phase 3 (Reflection)       ████████████████████  Completed
Phase 4 (Predictive)       ████████████████████  Completed
Phase 5 (Hardening)        ███████████████████░  In progress (only release tag remaining)
Phase 6 (Channel Arch.)    ████████████████████  Completed
Phase 7 (Telegram)         ███████████████████░  Completed (e2e tests remaining)
Phase 8 (Telegram UX)      ░░░░░░░░░░░░░░░░░░░░  Not started
```

Each phase produces a **testable deliverable** independently of subsequent ones.

---

## Design Notes

### Why Google ADK
- `LlmAgent` natively supports tools, system instruction, state management
- `SequentialAgent` and `ParallelAgent` for orchestrating Reflection and Predictive
- `InMemorySessionService` for development, replaceable with persistence in production
- Google ecosystem (Gemini) as default, but not binding

### Architectural Principles
1. **Every component is replaceable**: Mem0, Qdrant, the LLM provider are all swappable
2. **Zero mandatory cloud dependencies**: everything runs locally with Docker + Ollama
3. **Memory-first**: memory is not an add-on, it is the heart of the system
4. **Async by default**: all I/O operations are async
5. **Test-driven**: every phase includes tests before the deliverable

### Why Telegram (and not a CLI)
- The Digital Brain must be **reachable where the user already communicates**
- Telegram has an excellent, free official Bot API with no business requirements
- The conversational interface is **native** on Telegram — no onboarding needed
- The `ChannelPlugin` pattern (inspired by OpenClaw) makes it possible to add future channels (Discord, Slack, WhatsApp...) without touching the core

### Multimodal Media Handling
- The Digital Brain processes **all input types**: text, images, audio, video, documents
- **Strategy**: media are downloaded from the channel (e.g. Telegram `getFile`), converted to Google ADK `types.Part`, and passed directly to the multimodal model (Gemini) along with text
- **Flow**: `media received → download bytes → types.Part.from_bytes(data, mime_type) → Content(parts=[text, *media]) → Gemini`
- **Memory**: the AI describes/interprets the media and saves the text description to memory (Mem0 remains text-only for embeddings). Example: user sends a photo of a dish → AI responds "Looks like pasta carbonara!" → saves to memory "The user shared a photo of pasta carbonara"
- **LLM requirement**: a multimodal model is needed (Gemini Flash/Pro). If the configured provider doesn't support media (e.g. Ollama with a text-only model), the system notifies the user that media is not supported with that provider
- **Limits**: configurable maximum file size (default 20MB), MIME type allowlist for security

### Key Channel Decisions
1. **Telegram as primary channel**
   - Official Bot API, free, no commercial prerequisites
   - Supports: markdown, inline keyboards, native commands, groups, forum topics, media
   - Both webhook and polling modes supported
   - WhatsApp deferred: requires Meta Business account, complex setup, and the Cloud API has limitations (template messages, 24h windows)
2. **`python-telegram-bot` (not grammY)**
   - OpenClaw uses grammY (TypeScript). Python equivalent: `python-telegram-bot` (PTB)
   - PTB is the most mature library, async-native, with excellent documentation
   - Alternative evaluated: `aiogram` (lighter, more FastAPI-friendly) — final decision during Phase 7
3. **Channel Plugin as ABC, not PluginRuntime**
   - OpenClaw uses dependency injection via singleton runtime — Node/TypeScript pattern
   - In Python we use ABC + dependency injection via FastAPI — more idiomatic and testable
4. **Debouncing, media buffering, text fragment reassembly: patterns from OpenClaw**
   - Essential patterns for real chat UX — without debouncing, 5 rapid messages → 5 separate AI responses
   - Rewritten in Python asyncio, but identical logic

---

*Plan created for the Digital Brain project — based on the series "From Predictive Coding to Digital Brain" by Matteo Gazzurelli*
*Phases 6-8 inspired by the analysis of the OpenClaw repository (https://github.com/openclaw/openclaw)*
