# Digital Brain

A cognitive architecture for AI agents with persistent memory, inspired by **Predictive Coding** and **Active Inference**.

Built on [Google ADK](https://google.github.io/adk-docs/) + [Mem0](https://github.com/mem0ai/mem0), the Digital Brain gives LLM agents the ability to remember, consolidate, and anticipate — mimicking the human memory lifecycle.

## Quick Start

```bash
# 1. Start infrastructure
docker compose up -d qdrant

# 2. Install dependencies
uv sync --extra dev

# 3. Configure
cp .env.example .env
# Edit .env with your API keys

# 4. Run
uv run uvicorn digital_brain.api.app:app --reload
```

The API is available at `http://localhost:8000`. Check health at `GET /health`.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       DIGITAL BRAIN                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │               GOOGLE ADK AGENT LAYER                  │  │
│  │                                                       │  │
│  │  ┌──────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │ Conversation │  │ Reflection  │  │ Predictive  │  │  │
│  │  │    Agent     │  │   Agent     │  │   Agent     │  │  │
│  │  └──────┬───────┘  └──────┬──────┘  └──────┬──────┘  │  │
│  └─────────┼─────────────────┼─────────────────┼─────────┘  │
│            │                 │                 │            │
│  ┌─────────▼─────────────────▼─────────────────▼─────────┐  │
│  │                    MEMORY LAYER (Mem0)                 │  │
│  │   ┌──────────┐   ┌──────────┐   ┌──────────────┐     │  │
│  │   │  Vector  │   │  Graph   │   │  Key-Value   │     │  │
│  │   │ (Qdrant) │   │ (Neo4j)  │   │   (Redis)    │     │  │
│  │   └──────────┘   └──────────┘   └──────────────┘     │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                  │
│  ┌───────────────────────▼───────────────────────────────┐  │
│  │                    LLM LAYER                          │  │
│  │         (Gemini / Ollama / OpenAI)                    │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
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

## Development

```bash
# Install dev dependencies
uv sync --extra dev

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
| API | FastAPI + Uvicorn |
| Scheduling | APScheduler |
| Infrastructure | Docker Compose |
| Testing | pytest + asyncio |
| Linting | ruff |
| Package Manager | uv |

## License

Apache 2.0
