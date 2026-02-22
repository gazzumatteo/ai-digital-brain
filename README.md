# Digital Brain

A cognitive architecture for AI agents with persistent memory, inspired by **Predictive Coding** and **Active Inference**.

Built on [Google ADK](https://google.github.io/adk-docs/) + [Mem0](https://github.com/mem0ai/mem0), the Digital Brain gives LLM agents the ability to remember, consolidate, and anticipate — mimicking the human memory lifecycle.

Communicate with your Digital Brain via **Telegram** (text, images, audio, video, documents) or the **REST API**.

## Quick Start

### Requisiti

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- Docker e Docker Compose
- Una chiave API Google (per Gemini) **oppure** Ollama installato in locale

### Installazione

```bash
# 1. Clona il repository
git clone https://github.com/gazzumatteo/ai-digital-brain.git
cd ai-digital-brain

# 2. Avvia l'infrastruttura (Qdrant vector store)
docker compose up -d qdrant

# 3. Installa le dipendenze
uv sync --extra dev

# 4. Configura le variabili d'ambiente
cp .env.example .env
# Modifica .env con le tue API key (vedi sezione Configurazione)

# 5. Avvia il server
uv run uvicorn digital_brain.api.app:app --reload
```

L'API e disponibile su `http://localhost:8000`. Verifica lo stato con `GET /health`.

### Setup con Telegram Bot

Per usare il Digital Brain via Telegram:

```bash
# 1. Crea un bot su Telegram parlando con @BotFather
#    - Invia /newbot e segui le istruzioni
#    - Copia il token del bot

# 2. Aggiungi le variabili nel tuo .env
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234...
TELEGRAM_DM_POLICY=open

# 3. Avvia il server (il bot si avvia in polling mode)
uv run uvicorn digital_brain.api.app:app --reload
```

Il bot risponde ai messaggi privati e, nei gruppi, solo quando viene menzionato con `@nomebot`.

#### Comandi Telegram

| Comando | Descrizione |
|---------|-------------|
| `/start` | Messaggio di benvenuto |
| `/help` | Lista comandi disponibili |
| `/memories` | Mostra le tue memorie salvate |
| `/forget` | Cancella tutte le tue memorie |
| `/reflect` | Avvia la riflessione sulle memorie |

#### Media supportati

Il bot elabora tutti i tipi di media grazie al modello multimodale (Gemini):

- **Immagini** (JPEG, PNG, WebP, GIF)
- **Audio e note vocali** (OGG, MP3, WAV)
- **Video e video note** (MP4, WebM)
- **Documenti** (PDF)

I media vengono scaricati, convertiti in `types.Part` di Google ADK e passati direttamente a Gemini. La descrizione generata dall'AI viene salvata come memoria testuale.

## Architettura

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
| `POST` | `/webhooks/telegram` | Webhook per Telegram Bot API |
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
| `TELEGRAM_ENABLED` | `false` | Abilita il bot Telegram |
| `TELEGRAM_BOT_TOKEN` | — | Token del bot da @BotFather |
| `TELEGRAM_WEBHOOK_URL` | — | URL webhook (se vuoto, usa polling) |
| `TELEGRAM_WEBHOOK_SECRET` | — | Secret per verificare le richieste webhook |
| `TELEGRAM_DM_POLICY` | `pairing` | Policy accesso: `open`, `pairing`, `disabled` |
| `TELEGRAM_ALLOW_FROM` | `[]` | Lista Telegram user ID pre-autorizzati |
| `TELEGRAM_DEBOUNCE_MS` | `1500` | Millisecondi di attesa per coalizzare messaggi rapidi |

**DM Policy:**
- `open` — Tutti possono interagire con il bot
- `pairing` — Solo gli utenti nella allowlist (utile per uso personale)
- `disabled` — DM completamente disabilitati

**Modalita di ricezione:**
- **Polling** (default): il bot interroga periodicamente i server Telegram. Ideale per sviluppo locale, non richiede un URL pubblico.
- **Webhook**: Telegram invia gli aggiornamenti a un URL pubblico. Richiede HTTPS e un dominio raggiungibile. Imposta `TELEGRAM_WEBHOOK_URL` e opzionalmente `TELEGRAM_WEBHOOK_SECRET`.

### Media

| Variable | Default | Description |
|----------|---------|-------------|
| `MEDIA_MAX_FILE_SIZE_MB` | `20` | Dimensione massima file accettato (MB) |
| `MEDIA_ALLOWED_TYPES` | `image/*, audio/*, video/*, application/pdf` | MIME types permessi (supporta wildcard) |

### Observability

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FORMAT` | `json` | `json` (structured) or `text` |
| `RATE_LIMIT_ENABLED` | `true` | Enable API rate limiting |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `60` | Max requests per IP per minute |

## Docker

```bash
# Stack completo (Qdrant + app)
docker compose up -d

# Con Neo4j graph store
docker compose --profile graph up -d

# Con Ollama LLM locale
docker compose --profile local up -d
```

Per abilitare Telegram in Docker, aggiungi le variabili nel file `.env`:

```bash
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=il-tuo-token
TELEGRAM_DM_POLICY=open
```

In modalita webhook (produzione), imposta anche:

```bash
TELEGRAM_WEBHOOK_URL=https://tuodominio.com/webhooks/telegram
TELEGRAM_WEBHOOK_SECRET=un-secret-casuale
```

## Sviluppo

```bash
# Installa le dipendenze di sviluppo
uv sync --extra dev

# Avvia il server in modalita sviluppo
uv run uvicorn digital_brain.api.app:app --reload

# Esegui i test
uv run pytest tests/ -v

# Esegui i test con coverage
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
