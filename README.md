# Digital Brain

[![CI](https://github.com/gazzumatteo/ai-digital-brain/actions/workflows/ci.yml/badge.svg)](https://github.com/gazzumatteo/ai-digital-brain/actions/workflows/ci.yml)
![Tests](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/gazzumatteo/c2dba38f3b95c6a6d0aee6915bd6bda1/raw/ai-digital-brain-junit-tests.json)
![Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/gazzumatteo/c2dba38f3b95c6a6d0aee6915bd6bda1/raw/ai-digital-brain-cobertura-coverage.json)

A cognitive architecture for AI agents with persistent memory, inspired by **Predictive Coding** and **Active Inference**.

Built on [Google ADK](https://google.github.io/adk-docs/) + [Mem0](https://github.com/mem0ai/mem0), the Digital Brain gives LLM agents the ability to remember, consolidate, and anticipate — mimicking the human memory lifecycle.

Communicate with your Digital Brain via **Telegram** (text, images, audio, video, documents) or the **REST API**.

## Quick Start

### Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- Docker and Docker Compose
- A Google API key (for Gemini) **or** Ollama installed locally

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/gazzumatteo/ai-digital-brain.git
cd ai-digital-brain

# 2. Start the infrastructure (Qdrant vector store)
docker compose up -d qdrant

# 3. Install dependencies
uv sync --extra dev

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your API keys (see Configuration section)

# 5. Start the server
uv run uvicorn digital_brain.api.app:app --reload
```

The API is available at `http://localhost:8000`. Check status with `GET /health`.

### Telegram Bot Setup

To use the Digital Brain via Telegram:

1. **Create a bot** on Telegram by talking to `@BotFather` — send `/newbot` and copy the token.

2. **Configure `.env`:**

```bash
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234...
TELEGRAM_DM_POLICY=open
```

3. **Start the server** (the bot starts in polling mode):

```bash
uv run uvicorn digital_brain.api.app:app --reload
```

The bot responds to private messages and, in groups, only when mentioned with `@botname`.

> **Note on DM Policy:** The default is `pairing`, which silently blocks all messages from users not listed in `TELEGRAM_ALLOW_FROM`. To get started quickly, use `open`. To restrict access to your account only, use `pairing` with your Telegram user ID (you can find it by messaging `@userinfobot` on Telegram):
>
> ```bash
> TELEGRAM_DM_POLICY=pairing
> TELEGRAM_ALLOW_FROM=["123456789"]
> ```

#### Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | List available commands |
| `/memories` | Show your saved memories |
| `/forget` | Delete all your memories |
| `/reflect` | Trigger memory reflection |

#### Supported Media

The bot processes all media types using the multimodal model (Gemini):

- **Images** (JPEG, PNG, WebP, GIF)
- **Audio and voice notes** (OGG, MP3, WAV)
- **Video and video notes** (MP4, WebM)
- **Documents** (PDF)

Media files are downloaded, converted to Google ADK `types.Part` objects, and passed directly to Gemini. The AI-generated description is saved as a text memory.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       DIGITAL BRAIN                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                  CHANNEL LAYER                         │  │
│  │                                                        │  │
│  │  ┌──────────┐     ┌─────────────────────────────────┐  │  │
│  │  │ Telegram │     │  Inbound Pipeline               │  │  │
│  │  │   Bot    │────▶│  security → debounce → media    │  │  │
│  │  │   API    │     │  → dispatch → chunked response  │  │  │
│  │  └──────────┘     └──────────────┬──────────────────┘  │  │
│  └──────────────────────────────────┼─────────────────────┘  │
│                                     │                        │
│  ┌──────────────────────────────────▼─────────────────────┐  │
│  │               GOOGLE ADK AGENT LAYER                   │  │
│  │                                                        │  │
│  │  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐  │  │
│  │  │ Conversation │  │ Reflection  │  │  Predictive  │  │  │
│  │  │    Agent     │  │   Agent     │  │    Agent     │  │  │
│  │  └──────┬───────┘  └──────┬──────┘  └──────┬───────┘  │  │
│  └─────────┼─────────────────┼─────────────────┼──────────┘  │
│            │                 │                 │             │
│  ┌─────────▼─────────────────▼─────────────────▼──────────┐  │
│  │                   MEMORY LAYER (Mem0)                   │  │
│  │   ┌──────────┐   ┌──────────┐   ┌──────────────┐      │  │
│  │   │  Vector  │   │  Graph   │   │  Key-Value   │      │  │
│  │   │ (Qdrant) │   │ (Neo4j)  │   │   (Redis)    │      │  │
│  │   └──────────┘   └──────────┘   └──────────────┘      │  │
│  └────────────────────────────────────────────────────────┘  │
│                          │                                   │
│  ┌───────────────────────▼────────────────────────────────┐  │
│  │                    LLM LAYER                           │  │
│  │          (Gemini / Ollama / OpenAI)                    │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Three Agents, One Brain

| Agent | Role | Schedule |
|-------|------|----------|
| **Conversation** | Memory-augmented dialogue (mnemonic loop: retrieve → generate → store) | On every request |
| **Reflection** | Memory consolidation — finds patterns, resolves contradictions, synthesises insights | Cron (default 03:00) |
| **Predictive** | Active inference — anticipates user needs and pre-loads relevant memories | Before each conversation |

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Send a message (memory-augmented response) |
| `GET` | `/memories/{user_id}` | List all memories for a user |
| `POST` | `/reflect/{user_id}` | Trigger memory consolidation |
| `DELETE` | `/memories/{memory_id}` | Delete a single memory |
| `DELETE` | `/memories/user/{user_id}` | Delete all user memories (GDPR) |
| `POST` | `/webhooks/telegram` | Webhook for Telegram Bot API |
| `GET` | `/health` | Health check with component status and metrics |

### `POST /chat`

```json
{
  "user_id": "alice",
  "message": "I just switched to a standing desk",
  "session_id": null,
  "enable_prediction": true
}
```

Response:

```json
{
  "response": "Great choice! I remember you mentioned back pain from sitting...",
  "user_id": "alice",
  "session_id": null
}
```

### `GET /health`

Returns component health, active configuration, and runtime metrics:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "components": { "qdrant": "healthy" },
  "config": {
    "llm_provider": "gemini",
    "llm_model": "gemini-3-flash-preview",
    "embedder_provider": "ollama"
  },
  "metrics": {
    "counters": { "chat_requests": 42 },
    "timers": { "chat_latency": { "count": 42, "avg_ms": 1200.5 } }
  }
}
```

## Configuration

All settings are controlled via environment variables (or `.env` file). See `.env.example` for the full list.

### LLM Provider

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `gemini` | `gemini`, `ollama`, or `openai` |
| `LLM_MODEL` | `gemini-3-flash-preview` | Model name |
| `GOOGLE_API_KEY` | — | Required for Gemini |
| `OPENAI_API_KEY` | — | Required for OpenAI |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |

### Embedder

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDER_PROVIDER` | `ollama` | `ollama`, `openai`, or `gemini` |
| `EMBEDDER_MODEL` | `nomic-embed-text:latest` | Embedding model |
| `EMBEDDING_DIMS` | `768` | Embedding dimensions |

### Infrastructure

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_HOST` | `localhost` | Qdrant vector store host |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `NEO4J_ENABLED` | `false` | Enable Neo4j graph store |

### Agents

| Variable | Default | Description |
|----------|---------|-------------|
| `REFLECTION_SCHEDULE_HOUR` | `3` | Hour (UTC) for digital sleep |
| `REFLECTION_SCHEDULE_MINUTE` | `0` | Minute for digital sleep |
| `REFLECTION_LOOKBACK_HOURS` | `24` | Hours of memories to review |
| `REFLECTION_MIN_MEMORIES` | `3` | Min memories before creating insights |
| `PREDICTION_CONFIDENCE_THRESHOLD` | `0.7` | Minimum confidence for pre-loading |
| `MAX_PRELOAD_MEMORIES` | `10` | Max memories to pre-load |
| `MAX_PRELOAD_TOKENS` | `2000` | Token budget for pre-loaded context |
| `MEMORY_TTL_DAYS` | `0` | Auto-expire memories (0 = disabled) |

### Telegram

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_ENABLED` | `false` | Enable the Telegram bot |
| `TELEGRAM_BOT_TOKEN` | — | Bot token from @BotFather |
| `TELEGRAM_WEBHOOK_URL` | — | Webhook URL (if empty, uses polling) |
| `TELEGRAM_WEBHOOK_SECRET` | — | Secret to verify webhook requests |
| `TELEGRAM_DM_POLICY` | `pairing` | Access policy: `open`, `pairing`, `disabled` |
| `TELEGRAM_ALLOW_FROM` | `[]` | Pre-authorized Telegram user IDs |
| `TELEGRAM_DEBOUNCE_MS` | `1500` | Milliseconds to wait before coalescing rapid messages |

**DM Policy:**
- `open` — Anyone can interact with the bot (recommended to get started)
- `pairing` — Only users in `TELEGRAM_ALLOW_FROM` can interact. Messages from unknown users are silently ignored. To find your Telegram user ID, message `@userinfobot` on Telegram.
- `disabled` — DMs completely disabled

**Receiving mode:**
- **Polling** (default): the bot periodically polls Telegram servers. Ideal for local development, no public URL required.
- **Webhook**: Telegram sends updates to a public URL. Requires HTTPS and a reachable domain. Set `TELEGRAM_WEBHOOK_URL` and optionally `TELEGRAM_WEBHOOK_SECRET`.

### Media

| Variable | Default | Description |
|----------|---------|-------------|
| `MEDIA_MAX_FILE_SIZE_MB` | `20` | Maximum accepted file size (MB) |
| `MEDIA_ALLOWED_TYPES` | `image/*, audio/*, video/*, application/pdf` | Allowed MIME types (supports wildcards) |

### Observability

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FORMAT` | `json` | `json` (structured) or `text` |
| `RATE_LIMIT_ENABLED` | `true` | Enable API rate limiting |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `60` | Max requests per IP per minute |

## Docker

```bash
# Full stack (Qdrant + app)
docker compose up -d

# With Neo4j graph store
docker compose --profile graph up -d

# With local Ollama LLM
docker compose --profile local up -d
```

To enable Telegram in Docker, add the variables to your `.env` file:

```bash
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_DM_POLICY=open
```

In webhook mode (production), also set:

```bash
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhooks/telegram
TELEGRAM_WEBHOOK_SECRET=a-random-secret
```

## Development

```bash
# Install dev dependencies
uv sync --extra dev

# Start the server in development mode
uv run uvicorn digital_brain.api.app:app --reload

# Run tests
uv run pytest tests/ -v

# Run tests with coverage
uv run pytest tests/ --cov=digital_brain --cov-report=term-missing

# Lint
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

### Scripts

```bash
# Seed demo memories
uv run python scripts/seed_memories.py

# Trigger reflection manually
uv run python scripts/run_reflection.py
```

## Stack

| Component | Technology |
|-----------|-----------|
| Agent Framework | Google ADK |
| Memory Layer | Mem0 |
| Vector Store | Qdrant |
| Graph Store | Neo4j (optional) |
| LLM | Gemini / Ollama / OpenAI |
| Messaging | Telegram Bot API (python-telegram-bot) |
| API | FastAPI + Uvicorn |
| Scheduling | APScheduler |
| Infrastructure | Docker Compose |
| Testing | pytest + asyncio |
| Linting | ruff |
| Package Manager | uv |

## License

Apache 2.0
