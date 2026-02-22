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
│                      DIGITAL BRAIN                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌────────────────────────────────────────────────────┐     │
│   │              GOOGLE ADK AGENT LAYER                │     │
│   │                                                    │     │
│   │  ┌──────────────┐  ┌─────────────┐  ┌──────────┐  │     │
│   │  │ Conversation │  │ Reflection  │  │Predictive│  │     │
│   │  │    Agent     │  │   Agent     │  │  Agent   │  │     │
│   │  └──────┬───────┘  └──────┬──────┘  └────┬─────┘  │     │
│   │         │                 │               │        │     │
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
│           └── routes.py           # Endpoints: /chat, /memories, /reflect
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
- [ ] Endpoint `DELETE /memories/user/{user_id}` — "right to be forgotten" completo
- [ ] Scoping rigoroso: nessun leak di memorie tra utenti diversi
- [ ] Nessun log di contenuti sensibili (sanitizzare prima del logging)
- [ ] Rate limiting sugli endpoint API

#### 5.2 Osservabilità
- [ ] Logging strutturato (JSON) con correlation ID per sessione
- [ ] Metriche:
  - Memorie create/consolidate/eliminate per ciclo di reflection
  - Latenza di retrieval
  - Accuratezza delle predizioni (hit rate)
  - Token consumati per operazione
- [ ] Health check endpoint: `/health`

#### 5.3 Configurabilità
- [ ] Supporto multi-provider LLM (Ollama, Gemini, OpenAI) via config
- [ ] Parametri di tuning esposti come variabili d'ambiente:
  - `REFLECTION_SCHEDULE` (cron expression)
  - `PREDICTION_CONFIDENCE_THRESHOLD`
  - `MEMORY_TTL_DAYS`
  - `MAX_PRELOAD_TOKENS`
- [ ] Profili predefiniti: `local` (Ollama), `cloud` (Gemini), `hybrid`

#### 5.4 Documentazione e Release
- [ ] README.md con:
  - Quick start (3 comandi per partire)
  - Architettura spiegata
  - Configurazione
  - API reference
- [ ] Script `scripts/seed_memories.py` per demo
- [ ] CI con GitHub Actions (lint, test, build Docker)
- [ ] Tag v0.1.0 e release

**Deliverable**: Repository open-source completo, forkabile, con documentazione.

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
Fase 1 (Fondamenta)     ████████████░░░░░░░░  Settimana 1-2
Fase 2 (Conversation)   ████████████░░░░░░░░  Settimana 2-3
Fase 3 (Reflection)     ████████████░░░░░░░░  Settimana 3-4
Fase 4 (Predictive)     ████████████░░░░░░░░  Settimana 4-5
Fase 5 (Hardening)      ████████████░░░░░░░░  Settimana 5-6
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
1. **Ogni componente &egrave; sostituibile**: Mem0, Qdrant, il provider LLM sono tutti swappabili
2. **Zero dipendenze cloud obbligatorie**: tutto gira in locale con Docker + Ollama
3. **Memory-first**: la memoria non &egrave; un add-on, &egrave; il cuore del sistema
4. **Async by default**: tutte le operazioni I/O sono async
5. **Test-driven**: ogni fase include test prima del deliverable

---

*Piano creato per il progetto Digital Brain — basato sulla serie "From Predictive Coding to Digital Brain" di Matteo Gazzurelli*
