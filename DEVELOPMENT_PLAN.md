# Digital Brain — Piano di Sviluppo

## Panoramica del Progetto

Implementazione di un **Digital Brain** basato sui principi di Predictive Coding, Active Inference e consolidamento durante il "sonno digitale", come descritto nella serie di articoli *"From Predictive Coding to Digital Brain"*.

**Stack tecnologico:**
- **Linguaggio**: Python 3.11+
- **Agent Framework**: Google ADK (Agent Development Kit)
- **Memory Layer**: Mem0 (Apache 2.0)
- **Vector Store**: Qdrant (self-hosted)
- **Graph Store**: Neo4j (opzionale)
- **LLM locale**: Ollama
- **LLM cloud**: Google Gemini (default per ADK), configurabile
- **Scheduling**: APScheduler
- **Infrastruttura**: Docker Compose

---

## Architettura ad Alto Livello

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
│   │        (Ollama / Gemini / configurabile)           │     │
│   └────────────────────────────────────────────────────┘     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Struttura del Progetto

```
ai-digital-brain/
├── docker-compose.yml              # Infrastruttura completa
├── Dockerfile                      # Immagine dell'applicazione
├── pyproject.toml                  # Dipendenze e metadata (uv/pip)
├── .env.example                    # Template variabili d'ambiente
├── .gitignore
├── README.md
│
├── src/
│   └── digital_brain/
│       ├── __init__.py
│       ├── config.py               # Configurazione centralizzata (Pydantic Settings)
│       │
│       ├── memory/                 # Layer di memoria (Mem0 wrapper)
│       │   ├── __init__.py
│       │   ├── manager.py          # MemoryManager: init e config Mem0
│       │   ├── tools.py            # ADK Tools: memory_store, memory_search, memory_get
│       │   └── schemas.py          # Pydantic models per memory entities
│       │
│       ├── agents/                 # Google ADK Agents
│       │   ├── __init__.py
│       │   ├── conversation.py     # ConversationAgent: dialogo con memoria
│       │   ├── reflection.py       # ReflectionAgent: consolidamento ("digital sleep")
│       │   ├── predictive.py       # PredictiveAgent: pre-loading proattivo
│       │   └── orchestrator.py     # Orchestratore principale
│       │
│       ├── channels/               # Multi-channel messaging layer (Fase 6+)
│       │   ├── __init__.py
│       │   ├── base.py             # ChannelPlugin ABC + InboundMessage/OutboundResult
│       │   ├── registry.py         # ChannelRegistry: registro canali attivi
│       │   ├── pipeline.py         # Inbound pipeline: normalize → dispatch
│       │   ├── media.py            # MediaProcessor: download, validazione, conversione ADK Part
│       │   ├── debounce.py         # Debouncer messaggi rapidi consecutivi
│       │   ├── chunking.py         # Text/markdown chunking per risposte lunghe
│       │   ├── security.py         # DM policy, pairing, allowlist
│       │   │
│       │   └── telegram/           # Telegram Bot API integration (Fase 7)
│       │       ├── __init__.py
│       │       ├── plugin.py       # TelegramChannel(ChannelPlugin)
│       │       ├── handlers.py     # Inbound: text, media, commands, groups
│       │       ├── send.py         # Outbound: invio messaggi/media
│       │       └── mapping.py      # Telegram user_id → brain user_id
│       │
│       ├── tools/                  # ADK Tools custom
│       │   ├── __init__.py
│       │   ├── calendar_tool.py    # (opzionale) Integrazione calendario
│       │   └── context_tool.py     # Segnali di contesto (ora, sessione, pattern)
│       │
│       ├── scheduler/              # Scheduling per Reflection Agent
│       │   ├── __init__.py
│       │   └── jobs.py             # Job definitions (APScheduler)
│       │
│       └── api/                    # Interfaccia HTTP (FastAPI)
│           ├── __init__.py
│           ├── app.py              # FastAPI app (o ADK dev server wrapper)
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
│   └── test_integration.py         # Test end-to-end con servizi reali
│
└── scripts/
    ├── seed_memories.py            # Popola memoria iniziale per demo
    └── run_reflection.py           # Trigger manuale del Reflection Agent
```

---

## Fasi di Sviluppo

### Fase 1 — Fondamenta (Infrastruttura + Memory Layer)

**Obiettivo**: Stack funzionante con Mem0 configurato e testabile.

#### 1.1 Setup del progetto
- [ ] Creare `pyproject.toml` con dipendenze:
  - `google-adk`
  - `mem0ai`
  - `fastapi`, `uvicorn`
  - `pydantic-settings`
  - `apscheduler`
  - `pytest`, `pytest-asyncio`
- [ ] Creare `.env.example` con tutte le variabili richieste
- [ ] Creare `.gitignore` (Python, .env, __pycache__, .venv, ecc.)
- [ ] Creare `Dockerfile` multi-stage (builder + runtime)
- [ ] Creare `docker-compose.yml` con servizi:
  - `qdrant` (vector store)
  - `neo4j` (graph store, opzionale)
  - `ollama` (LLM locale)
  - `app` (digital brain)

#### 1.2 Configurazione centralizzata
- [ ] `config.py` con Pydantic `BaseSettings`:
  - LLM provider (ollama/gemini/openai) + model name
  - Mem0 config (vector store, graph store, embedder)
  - Parametri di consolidamento (schedule, threshold, TTL)
  - Scoping defaults (user_id, agent_id)

#### 1.3 Memory Manager (Mem0 wrapper)
- [ ] `memory/manager.py` — classe `MemoryManager`:
  - `__init__`: inizializza Mem0 con config per Qdrant + Neo4j + Ollama embeddings
  - `add(messages, user_id, metadata)`: wrapper su `memory.add()`
  - `search(query, user_id, limit)`: wrapper su `memory.search()`
  - `get_all(user_id)`: tutte le memorie di un utente
  - `delete(memory_id)`: cancellazione singola memoria
  - `get_recent(user_id, hours)`: memorie delle ultime N ore
- [ ] `memory/schemas.py` — Pydantic models:
  - `MemoryEntry`: id, content, user_id, created_at, metadata, score
  - `MemorySearchResult`: lista di MemoryEntry con score
- [ ] Test unitari con mock di Mem0

#### 1.4 Memory Tools per ADK
- [ ] `memory/tools.py` — funzioni da esporre come ADK FunctionTool:
  ```python
  def memory_store(content: str, user_id: str, metadata: dict = None) -> str:
      """Salva un'informazione nella memoria a lungo termine."""

  def memory_search(query: str, user_id: str, limit: int = 5) -> list[dict]:
      """Cerca memorie rilevanti per la query."""

  def memory_get_all(user_id: str) -> list[dict]:
      """Recupera tutte le memorie di un utente."""
  ```

**Deliverable**: `docker compose up` avvia Qdrant + Ollama, i test passano.

---

### Fase 2 — Conversation Agent (Mnemonic Loop base)

**Obiettivo**: Agente conversazionale con memoria persistente funzionante.

#### 2.1 Conversation Agent con Google ADK
- [ ] `agents/conversation.py` — `create_conversation_agent()`:
  ```python
  from google.adk.agents import LlmAgent
  from google.adk.tools import FunctionTool

  conversation_agent = LlmAgent(
      name="conversation_agent",
      model="gemini-2.0-flash",  # o ollama via LiteLLM
      instruction="""Sei un assistente personale con memoria persistente.
      Prima di rispondere, cerca sempre nella memoria informazioni rilevanti.
      Dopo la conversazione, salva i fatti importanti nella memoria.""",
      tools=[
          FunctionTool(memory_search),
          FunctionTool(memory_store),
      ],
  )
  ```
- [ ] System prompt con istruzioni per:
  - Cercare nella memoria **prima** di rispondere (retrieval)
  - Estrarre fatti, preferenze, entità dalla conversazione (extraction)
  - Salvare nella memoria i nuovi fatti (storage)
- [ ] Gestione del `session_id` e `user_id` tramite ADK Session/State

#### 2.2 API HTTP
- [ ] `api/app.py` — FastAPI con endpoint:
  - `POST /chat` — input: messaggio utente + user_id, output: risposta agente
  - `GET /memories/{user_id}` — lista memorie
  - `DELETE /memories/{memory_id}` — cancella memoria (right to be forgotten)
- [ ] Integrazione con ADK Runner per esecuzione dell'agente:
  ```python
  from google.adk.runners import Runner
  from google.adk.sessions import InMemorySessionService

  runner = Runner(
      agent=conversation_agent,
      app_name="digital_brain",
      session_service=InMemorySessionService(),
  )
  ```

#### 2.3 Test end-to-end
- [ ] Test: invia messaggio → agente risponde → memoria salvata
- [ ] Test: invia secondo messaggio → agente recupera memoria precedente
- [ ] Test: verifica che le memorie persistano tra sessioni diverse

**Deliverable**: Chat funzionante che ricorda tra sessioni. `POST /chat` → risposta con contesto memorizzato.

---

### Fase 3 — Reflection Agent ("Digital Sleep")

**Obiettivo**: Consolidamento automatico delle memorie.

#### 3.1 Reflection Agent
- [ ] `agents/reflection.py` — `create_reflection_agent()`:
  ```python
  reflection_agent = LlmAgent(
      name="reflection_agent",
      model="gemini-2.0-flash",
      instruction="""Sei un agente di consolidamento della memoria.
      Analizza le memorie recenti e:
      1. Identifica pattern ricorrenti
      2. Trova e risolvi contraddizioni
      3. Sintetizza insight di alto livello
      4. Marca come obsolete le memorie superate""",
      tools=[
          FunctionTool(memory_get_all),
          FunctionTool(memory_search),
          FunctionTool(memory_store),
          FunctionTool(memory_delete),
      ],
  )
  ```
- [ ] Logica di consolidamento:
  - **GATHER**: recupera memorie delle ultime 24h
  - **ANALYZE**: LLM identifica pattern, conflitti, ridondanze
  - **SYNTHESIZE**: crea memorie sintetiche di livello superiore (episodic → semantic)
  - **PRUNE**: archivia/cancella memorie obsolete o duplicate
- [ ] Metadata sulle memorie:
  - `memory_type`: `episodic` | `semantic` | `insight`
  - `confidence`: 0.0-1.0
  - `source_count`: quante memorie episodiche supportano un insight
  - `ttl`: time-to-live opzionale

#### 3.2 Scheduling
- [ ] `scheduler/jobs.py` — configurazione APScheduler:
  ```python
  scheduler.add_job(
      run_reflection,
      trigger="cron",
      hour=3,  # "digital sleep" alle 03:00
      minute=0,
  )
  ```
- [ ] Endpoint manuale: `POST /reflect/{user_id}` per trigger on-demand
- [ ] Logging dettagliato: quante memorie analizzate, consolidate, eliminate

#### 3.3 Safeguard
- [ ] Soglia minima di occorrenze prima di sintetizzare (evita false pattern)
- [ ] Mantenere link tra memorie sintetiche e sorgenti episodiche
- [ ] TTL sulle memorie consolidate con recency weighting
- [ ] Test: verifica che memorie duplicate vengano fuse
- [ ] Test: verifica che contraddizioni vengano risolte (newer wins)

**Deliverable**: Reflection Agent eseguibile via cron o manualmente. Le memorie si consolidano.

---

### Fase 4 — Predictive Engine (Active Inference)

**Obiettivo**: Pre-caricamento proattivo delle memorie basato sul contesto.

#### 4.1 Context Signals
- [ ] `tools/context_tool.py` — raccolta segnali:
  ```python
  def get_context_signals(user_id: str) -> dict:
      """Restituisce segnali contestuali per la predizione."""
      return {
          "time_of_day": "morning|afternoon|evening",
          "day_of_week": "monday|...|sunday",
          "recent_topics": [...],         # ultimi topic delle sessioni recenti
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
      instruction="""Basandoti sui segnali di contesto e sulle memorie recenti,
      prevedi quali informazioni l'utente probabilmente avrà bisogno.
      Restituisci una lista di query di ricerca da pre-caricare.""",
      tools=[
          FunctionTool(get_context_signals),
          FunctionTool(memory_search),
      ],
  )
  ```
- [ ] Flusso di pre-loading:
  1. Utente avvia sessione → raccogli context signals
  2. Predictive Agent genera query predittive
  3. Pre-fetch memorie rilevanti
  4. Inietta come "background knowledge" nel contesto del Conversation Agent
- [ ] Confidence threshold: pre-fetch solo se confidence > 0.7

#### 4.3 Integrazione con Conversation Agent
- [ ] `agents/orchestrator.py` — orchestrazione completa:
  ```python
  async def handle_session_start(user_id: str, session_id: str):
      # 1. Predictive pre-loading
      predictions = await run_predictive_agent(user_id)
      # 2. Pre-fetch memories
      preloaded = await prefetch_memories(predictions)
      # 3. Inject into conversation context
      return create_augmented_session(preloaded)
  ```
- [ ] Feedback loop: tracciare se le predizioni erano utili (l'utente ha effettivamente chiesto di quei topic?)

#### 4.4 Safeguard
- [ ] Cache TTL sulle predizioni (invalidare su cambio topic)
- [ ] Budget massimo di token per pre-loading
- [ ] Non annunciare le predizioni all'utente (evitare "creepy factor")
- [ ] Test: verifica che le predizioni siano pertinenti al contesto

**Deliverable**: L'agente anticipa le esigenze dell'utente, pre-caricando memorie rilevanti.

---

### Fase 5 — Hardening e Produzione

**Obiettivo**: Sistema robusto, documentato e pronto per il rilascio open-source.

#### 5.1 Privacy e Sicurezza
- [x] Endpoint `DELETE /memories/user/{user_id}` — "right to be forgotten" completo
- [x] Scoping rigoroso: nessun leak di memorie tra utenti diversi
  - Validazione `user_id` con regex (alfanumerico, 1-128 char)
  - Rifiuto di path-traversal, injection e caratteri speciali
  - Validazione a livello di Pydantic model e route
- [x] Nessun log di contenuti sensibili (sanitizzare prima del logging)
  - Modulo `logging_config.py` con pattern matching per API key (Google, OpenAI, GitHub), password, token
  - Sanitizzazione automatica su JSONFormatter e SanitizedTextFormatter
- [x] Rate limiting sugli endpoint API
  - `RateLimitMiddleware` con sliding window per IP
  - Configurabile via `RATE_LIMIT_ENABLED` e `RATE_LIMIT_REQUESTS_PER_MINUTE`

#### 5.2 Osservabilità
- [x] Logging strutturato (JSON) con correlation ID per sessione
  - `CorrelationIDMiddleware` genera/propaga `X-Correlation-ID` su ogni request
  - `JSONFormatter` emette log come JSON single-line con timestamp, level, correlation_id, extra fields
  - `SanitizedTextFormatter` per modalità testo con redaction
  - Configurabile via `LOG_LEVEL` e `LOG_FORMAT` (json/text)
- [x] Metriche:
  - `MetricsCollector` thread-safe con counters e timers
  - Tracciamento: chat_requests, reflection_requests, memory ops, rate_limited
  - Timer: chat_latency, reflection_latency, prediction_latency, conversation_latency, http_request
  - HTTP status code counters (http_200, http_429, ecc.)
- [x] Health check endpoint: `/health`
  - Verifica connettività Qdrant e Neo4j (se abilitato)
  - Stato: "ok" o "degraded"
  - Espone config attiva (provider, model) e snapshot metriche

#### 5.3 Configurabilità
- [x] Supporto multi-provider LLM (Ollama, Gemini, OpenAI) via config
- [x] Parametri di tuning esposti come variabili d'ambiente:
  - `REFLECTION_SCHEDULE_HOUR`, `REFLECTION_SCHEDULE_MINUTE`
  - `PREDICTION_CONFIDENCE_THRESHOLD`
  - `MEMORY_TTL_DAYS`
  - `MAX_PRELOAD_TOKENS`
  - `LOG_LEVEL`, `LOG_FORMAT`
  - `RATE_LIMIT_ENABLED`, `RATE_LIMIT_REQUESTS_PER_MINUTE`
- [x] Profili via Docker Compose: `local` (Ollama), `graph` (Neo4j)

#### 5.4 Documentazione e Release
- [x] README.md con:
  - Quick start (4 comandi per partire)
  - Diagramma architettura ASCII
  - Tabella agenti con ruoli
  - API reference completa con esempi request/response
  - Tabelle configurazione per ogni sezione
  - Istruzioni Docker e sviluppo
- [x] Script `scripts/seed_memories.py` per demo
- [x] CI con GitHub Actions (lint, test, coverage)
- [ ] Tag v0.1.0 e release

**Deliverable**: Repository open-source completo, forkabile, con documentazione.

---

### Fase 6 — Channel Architecture (Infrastruttura Multi-Canale)

**Obiettivo**: Creare l'astrazione che permette al Digital Brain di comunicare su qualsiasi canale (Telegram e futuri) tramite un'interfaccia unificata.

> *Pattern ispirato a OpenClaw: `ChannelPlugin` interface — l'unica astrazione che conta. Ogni dettaglio specifico del canale (formato messaggi, API, autenticazione, formato target) è incapsulato dietro un contratto comune. L'AI layer non sa e non deve sapere se un messaggio viene da Telegram o WhatsApp.*

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
      file_id: str             # ID del file nel canale di origine (es. Telegram file_id)
      file_size: int | None = None
      filename: str | None = None
      duration_seconds: float | None = None   # Per audio/video
      width: int | None = None                # Per immagini/video
      height: int | None = None               # Per immagini/video
      caption: str | None = None              # Caption opzionale del media

  @dataclass
  class InboundMessage:
      channel: str            # "telegram" | future channels
      chat_id: str            # ID univoco della chat
      sender_id: str          # ID del mittente
      sender_name: str        # Nome visualizzato
      text: str               # Testo del messaggio (o caption se solo media)
      media: list[MediaAttachment]  # Media allegati (immagini, audio, video, documenti)
      reply_to_id: Optional[str] = None
      thread_id: Optional[str] = None
      raw: dict = None        # Payload originale del canale

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
          """Avvia ricezione messaggi (webhook, polling, WS)."""

      @abstractmethod
      async def stop(self) -> None:
          """Shutdown graceful."""

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
- [x] `channels/registry.py` — Registro dei canali attivi:
  ```python
  class ChannelRegistry:
      def register(self, plugin: ChannelPlugin) -> None: ...
      def get(self, channel_id: str) -> ChannelPlugin: ...
      def list_channels(self) -> list[str]: ...
      async def start_all(self, abort: asyncio.Event) -> None: ...
      async def stop_all(self) -> None: ...
      async def health_check_all(self) -> dict[str, dict]: ...
  ```

#### 6.3 Inbound Pipeline (ispirata a OpenClaw)
- [x] `channels/pipeline.py` — Pipeline di elaborazione messaggi in arrivo:
  1. **Normalize**: converti evento raw del canale → `InboundMessage` standard
  2. **Security check**: verifica pairing/allowlist
  3. **Debounce**: coalizza messaggi rapidi consecutivi dallo stesso utente
  4. **Resolve session**: mappa `(channel, chat_id)` → `(user_id, session_key)`
  5. **Resolve media**: scarica file binari via canale → `bytes`, costruisci `types.Part` multimodali per ADK
  6. **Dispatch to AI**: costruisci `types.Content(parts=[text_part, *media_parts])` e inoltra al Conversation Agent
  7. **Send response**: risposta AI → canale di origine via `send_text()` o `send_media()`

#### 6.3.1 Media Processing
- [x] `channels/media.py` — Gestione media nel pipeline:
  ```python
  class MediaProcessor:
      """Scarica media dal canale e li converte in types.Part per Google ADK."""

      async def download(self, channel: ChannelPlugin, attachment: MediaAttachment) -> bytes:
          """Scarica il file binario dal canale di origine."""

      def to_adk_part(self, data: bytes, mime_type: str) -> types.Part:
          """Converte bytes + mime_type in un types.Part per Gemini multimodale."""
          # Gemini accetta: image/*, audio/*, video/*, application/pdf
          return types.Part.from_bytes(data=data, mime_type=mime_type)

      async def process_attachments(
          self, channel: ChannelPlugin, attachments: list[MediaAttachment]
      ) -> list[types.Part]:
          """Pipeline completa: download → validazione → conversione ADK Parts."""
  ```
- [x] Validazione: dimensione massima file (configurabile, default 20MB)
- [x] MIME type allowlist (evita eseguibili, archivi malevoli)
- [x] Tipi supportati dal LLM multimodale:
  - **Immagini**: `image/jpeg`, `image/png`, `image/webp`, `image/gif` → passate direttamente a Gemini
  - **Audio**: `audio/ogg`, `audio/mpeg`, `audio/wav` → passati a Gemini (supporto nativo)
  - **Video**: `video/mp4`, `video/webm` → passati a Gemini (supporto nativo)
  - **Documenti**: `application/pdf` → passato a Gemini; altri formati → estrazione testo se possibile

#### 6.4 Inbound Debouncer (pattern da OpenClaw)
- [x] `channels/debounce.py` — Coalizza messaggi rapidi:
  ```python
  class InboundDebouncer:
      """Previene 5 risposte AI per 5 messaggi consecutivi rapidi.
      Aspetta debounce_ms dopo l'ultimo messaggio, poi flasha tutto come uno."""

      def __init__(self, debounce_ms: int = 1500, on_flush: Callable): ...
      async def enqueue(self, key: str, message: InboundMessage) -> None: ...
  ```

#### 6.5 Security — DM Policy & Pairing (pattern da OpenClaw)
- [x] `channels/security.py` — Controllo accesso:
  ```python
  class DmPolicyEnforcer:
      """Tre modalità: 'open' (tutti), 'pairing' (allowlist + approvazione), 'disabled'."""
      def check_access(self, channel: str, sender_id: str) -> tuple[bool, str]: ...
      def approve(self, channel: str, sender_id: str) -> None: ...
  ```

#### 6.6 Outbound Chunking
- [x] `channels/chunking.py` — Spezza risposte lunghe:
  - Mode `markdown`: split preservando code blocks, liste, heading (Telegram, limite 4096 char)
  - Mode `text`: split greedy per lunghezza (per futuri canali senza supporto markdown)

#### 6.7 Configurazione Canali
- [x] Estensione di `config.py` con sezione channels:
  ```python
  # Telegram
  TELEGRAM_ENABLED: bool = False
  TELEGRAM_BOT_TOKEN: str = ""
  TELEGRAM_WEBHOOK_URL: str = ""    # Se vuoto → polling mode
  TELEGRAM_WEBHOOK_SECRET: str = ""
  TELEGRAM_DM_POLICY: str = "pairing"  # open | pairing | disabled
  TELEGRAM_ALLOW_FROM: list[str] = []
  TELEGRAM_DEBOUNCE_MS: int = 1500

  # Media processing
  MEDIA_MAX_FILE_SIZE_MB: int = 20        # Dimensione massima file accettato
  MEDIA_ALLOWED_TYPES: list[str] = [      # MIME types permessi
      "image/*", "audio/*", "video/*", "application/pdf"
  ]
  ```

#### 6.8 Test
- [x] Test unitari per ChannelPlugin ABC
- [x] Test per InboundDebouncer
- [x] Test per DmPolicyEnforcer
- [x] Test per text/markdown chunking
- [x] Test per ChannelRegistry lifecycle
- [x] Test per MediaProcessor (download, validazione MIME, conversione ADK Part)
- [x] Test per rifiuto file troppo grandi / MIME type non permessi

**Deliverable**: Infrastruttura multi-canale completa e testata, con supporto media multimodale. Nessun canale concreto ancora, ma il framework è pronto per accoglierli.

---

### Fase 7 — Integrazione Telegram

**Obiettivo**: Bot Telegram funzionante che permette di chattare con il Digital Brain via Telegram.

> *Libreria scelta: `python-telegram-bot` (matura, async-native, ottima documentazione). Alternativa: `aiogram` (più leggero, FastAPI-friendly). Decisione finale durante implementazione.*

#### 7.1 Telegram Plugin
- [ ] `channels/telegram/plugin.py` — `TelegramChannel(ChannelPlugin)`:
  - `channel_id()` → `"telegram"`
  - `capabilities()` → `{ chat_types: [direct, group], reactions: True, threads: True, media: True, commands: True }`
  - `start()` → avvia webhook o polling in base alla config
  - `send_text()` → invio messaggio via Bot API, con markdown parsing
  - `send_media()` → invio foto/video/documenti
  - `health_check()` → chiama `getMe()` e verifica connettività

#### 7.2 Webhook Endpoint (FastAPI)
- [ ] `api/webhooks.py` — endpoint webhook:
  ```python
  @router.post("/webhooks/telegram")
  async def telegram_webhook(request: Request):
      """Riceve update da Telegram Bot API."""
      # 1. Valida secret token (header X-Telegram-Bot-Api-Secret-Token)
      # 2. Parsa Update
      # 3. Normalizza → InboundMessage
      # 4. Passa alla pipeline
  ```
- [ ] Supporto polling mode (fallback per sviluppo locale senza tunnel)

#### 7.3 Inbound Handlers (pattern da OpenClaw)
- [ ] `channels/telegram/handlers.py`:
  - **Text messages**: normalizza, debounce, dispatch
  - **Photo/Image**: estrai `file_id` dalla risoluzione più alta, costruisci `MediaAttachment(type="image")`
  - **Audio/Voice**: estrai `file_id`, durata, MIME; voice notes → `type="voice"`, audio files → `type="audio"`
  - **Video/Video note**: estrai `file_id`, durata, dimensioni; video note (circolari) → `type="video"`
  - **Documenti**: estrai `file_id`, `file_name`, `mime_type`; supporta PDF, fogli, testo
  - **Media group buffering**: quando l'utente invia un album (più foto/video insieme), Telegram li consegna come update separati con stesso `media_group_id`. Bufferare e flushare come singolo `InboundMessage` con `media: list[MediaAttachment]`
  - **Caption handling**: se il media ha una caption, usarla come `text` del messaggio; se assente, `text = ""`
  - **Text fragment reassembly**: riassembla messaggi lunghi splittati da Telegram (>4096 char)
  - **Group messages**: mention gating — rispondi solo se il bot è menzionato (@botname)
  - **Commands**: `/start` (benvenuto), `/help`, `/forget` (cancella memorie)
  - **Sticker**: estrai `file_id` + emoji associato, costruisci `MediaAttachment(type="sticker")`

#### 7.4 Outbound — Invio Risposte
- [ ] `channels/telegram/send.py`:
  - Markdown-aware chunking (preserva code blocks, liste)
  - Limite: 4096 caratteri per messaggio
  - Supporto `reply_to_message_id` per risposte contestuali
  - Supporto forum topics (`message_thread_id`)
  - Rate limiting (30 msg/sec globale, 1 msg/sec per chat, limiti Bot API)

#### 7.5 Comandi Nativi Telegram
- [ ] `/start` — Messaggio di benvenuto + registrazione utente
- [ ] `/help` — Lista comandi disponibili
- [ ] `/forget` — Cancella tutte le memorie (right to be forgotten)
- [ ] `/memories` — Mostra un riepilogo delle memorie salvate
- [ ] `/reflect` — Trigger manuale del Reflection Agent

#### 7.6 User ID Mapping
- [ ] `channels/telegram/mapping.py`:
  - Mappa `telegram_user_id` → `digital_brain_user_id`
  - Prima interazione: crea automaticamente il mapping
  - Supporto per alias/nomi utente

#### 7.7 Test
- [ ] Test webhook handler con mock Update
- [ ] Test invio messaggi con mock Bot API
- [ ] Test text fragment reassembly
- [ ] Test media group buffering (album multi-foto)
- [ ] Test ricezione singola immagine → MediaAttachment corretto
- [ ] Test ricezione audio/voice → MediaAttachment con durata
- [ ] Test ricezione documento (PDF) → MediaAttachment con filename e MIME
- [ ] Test ricezione video → MediaAttachment con dimensioni e durata
- [ ] Test caption handling (media con/senza caption)
- [ ] Test mention gating in gruppi
- [ ] Test comandi nativi
- [ ] Test e2e: foto Telegram → AI descrive immagine → memoria salvata
- [ ] Test e2e: voice note → AI interpreta audio → risposta testuale

**Deliverable**: Bot Telegram funzionante con supporto multimodale. Testo, immagini, audio, video e documenti vengono tutti elaborati dall'AI. Testabile in locale con polling.

---

### Fase 8 — Hardening & UX Telegram

**Obiettivo**: Monitoring, UX ottimizzata e proactive outreach su Telegram.

#### 8.1 Monitoring & Osservabilità
- [ ] Metriche Telegram:
  - `telegram_messages_in`, `telegram_messages_out`
  - `telegram_latency_ms`
  - `telegram_errors`
- [ ] Health check esteso: `/health` include stato del canale Telegram
- [ ] Dashboard status: endpoint JSON con stato real-time del bot

#### 8.2 UX Ottimizzazioni per Telegram
- [ ] **Typing indicator**: mostra "sta scrivendo..." mentre l'AI genera (`sendChatAction`)
- [ ] **Risposte progressive**: edit-in-place del messaggio durante lo streaming LLM
- [ ] **Risposte contestuali**: reply-to sul messaggio originale dell'utente
- [ ] **Formattazione markdown**: sfruttare al massimo il supporto markdown di Telegram
- [ ] **Gestione errori graceful**: se l'AI fallisce, invia messaggio di scusa all'utente

#### 8.3 Proactive Outreach (Digital Brain → Utente)
- [ ] Il Predictive Agent può decidere di contattare proattivamente l'utente:
  - "Buongiorno! Oggi hai la riunione di progetto alle 10"
  - "Ho notato che non facciamo il punto sulla dieta da 3 giorni"
- [ ] Rispetta finestre temporali (non disturbare di notte)
- [ ] Canale preferito configurabile (per ora solo Telegram)

#### 8.4 Test
- [ ] Test: typing indicator funzionante
- [ ] Test: risposte progressive (edit-in-place)
- [ ] Test: proactive outreach con mock scheduler
- [ ] Test e2e: messaggio Telegram → risposta con memoria → metriche aggiornate

**Deliverable**: Bot Telegram con UX ottimizzata, monitoring completo e capacità proattive.

---

## Dipendenze Principali

| Package | Versione | Scopo |
|---------|----------|-------|
| `google-adk` | latest | Agent framework |
| `mem0ai` | latest | Memory layer |
| `fastapi` | ^0.115 | API HTTP |
| `uvicorn` | ^0.34 | ASGI server |
| `pydantic-settings` | ^2.0 | Configurazione |
| `apscheduler` | ^3.10 | Scheduling |
| `qdrant-client` | latest | Vector store client |
| `neo4j` | latest | Graph store client (opzionale) |
| `litellm` | latest | Proxy LLM multi-provider (opzionale) |
| `python-telegram-bot` | ^21.0 | Telegram Bot API (Fase 7) |
| `pytest` | ^8.0 | Testing |
| `pytest-asyncio` | latest | Test async |

---

## Docker Compose — Servizi

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
    profiles: ["graph"]  # opzionale

  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes: [ollama_data:/root/.ollama]
    profiles: ["local"]  # solo per LLM locale

  app:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [qdrant]
```

---

## Priorità e Ordine di Implementazione

```
Fase 1 (Fondamenta)        ████████████████████  Completata
Fase 2 (Conversation)      ████████████████████  Completata
Fase 3 (Reflection)        ████████████████████  Completata
Fase 4 (Predictive)        ████████████████████  Completata
Fase 5 (Hardening)         ███████████████████░  In corso (manca solo tag release)
Fase 6 (Channel Arch.)     ████████████████████  Completata
Fase 7 (Telegram)          ░░░░░░░░░░░░░░░░░░░░  Da iniziare
Fase 8 (Telegram UX)       ░░░░░░░░░░░░░░░░░░░░  Da iniziare
```

Ogni fase produce un **deliverable testabile** indipendentemente dalle successive.

---

## Note di Design

### Perch&eacute; Google ADK
- `LlmAgent` supporta nativamente tools, system instruction, state management
- `SequentialAgent` e `ParallelAgent` per orchestrare Reflection e Predictive
- `InMemorySessionService` per sviluppo, sostituibile con persistence in produzione
- Ecosistema Google (Gemini) come default, ma non vincolante

### Principi architetturali
1. **Ogni componente è sostituibile**: Mem0, Qdrant, il provider LLM sono tutti swappabili
2. **Zero dipendenze cloud obbligatorie**: tutto gira in locale con Docker + Ollama
3. **Memory-first**: la memoria non è un add-on, è il cuore del sistema
4. **Async by default**: tutte le operazioni I/O sono async
5. **Test-driven**: ogni fase include test prima del deliverable

### Perché Telegram (e non una CLI)
- Il Digital Brain deve essere **raggiungibile dove l'utente già comunica**
- Telegram ha un'API Bot ufficiale eccellente, gratuita, senza requisiti business
- L'interfaccia conversazionale è **nativa** su Telegram — nessun onboarding
- Il pattern `ChannelPlugin` (ispirato a OpenClaw) rende possibile aggiungere futuri canali (Discord, Slack, WhatsApp...) senza toccare il core

### Gestione media multimodale
- Il Digital Brain elabora **tutti i tipi di input**: testo, immagini, audio, video, documenti
- **Strategia**: i media vengono scaricati dal canale (es. Telegram `getFile`), convertiti in `types.Part` di Google ADK, e passati direttamente al modello multimodale (Gemini) insieme al testo
- **Flusso**: `media ricevuto → download bytes → types.Part.from_bytes(data, mime_type) → Content(parts=[text, *media]) → Gemini`
- **Memoria**: l'AI descrive/interpreta il media e salva la descrizione testuale in memoria (Mem0 resta text-only per gli embeddings). Esempio: utente invia foto di un piatto → AI risponde "Sembra pasta alla carbonara!" → salva in memoria "L'utente ha condiviso una foto di pasta alla carbonara"
- **Requisito LLM**: è necessario un modello multimodale (Gemini Flash/Pro). Se il provider configurato non supporta media (es. Ollama con modello text-only), il sistema notifica l'utente che i media non sono supportati con quel provider
- **Limiti**: dimensione massima file configurabile (default 20MB), MIME type allowlist per sicurezza

### Decisioni chiave per i canali
1. **Telegram come canale primario**
   - API Bot ufficiale, gratuita, senza prerequisiti commerciali
   - Supporta: markdown, inline keyboards, comandi nativi, gruppi, forum topics, media
   - Webhook e polling mode entrambi supportati
   - WhatsApp rimandato: richiede account Business Meta, configurazione complessa, e la Cloud API ha limitazioni (template messages, finestre 24h)
2. **`python-telegram-bot` (non grammY)**
   - OpenClaw usa grammY (TypeScript). Equivalente Python: `python-telegram-bot` (PTB)
   - PTB è la libreria più matura, async-native, con ottima documentazione
   - Alternativa valutata: `aiogram` (più leggero, più FastAPI-friendly) — decisione finale durante Fase 7
3. **Channel Plugin come ABC, non come PluginRuntime**
   - OpenClaw usa dependency injection via singleton runtime — pattern Node/TypeScript
   - In Python usiamo ABC + dependency injection via FastAPI — più idiomatico e testabile
4. **Debouncing, media buffering, text fragment reassembly: pattern da OpenClaw**
   - Pattern essenziali per UX reale su chat — senza debouncing, 5 messaggi rapidi → 5 risposte AI separate
   - Riscrittura in Python asyncio, ma logica identica

---

*Piano creato per il progetto Digital Brain — basato sulla serie "From Predictive Coding to Digital Brain" di Matteo Gazzurelli*
*Fasi 6-8 ispirate all'analisi del repository OpenClaw (https://github.com/openclaw/openclaw)*
