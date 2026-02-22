# Digital Brain

A cognitive architecture for AI agents with persistent memory, inspired by Predictive Coding and Active Inference.

## Quick Start

```bash
# 1. Start infrastructure
docker compose up -d qdrant

# 2. Install
uv sync --extra dev

# 3. Configure
cp .env.example .env
# Edit .env with your API keys

# 4. Run
uv run uvicorn digital_brain.api.app:app --reload
```

## Architecture

```
Conversation Agent  ←→  Memory Layer (Mem0)  ←→  Qdrant / Neo4j
Reflection Agent    ←→  Memory Layer (Mem0)  ←→  (scheduled consolidation)
Predictive Agent    ←→  Memory Layer (Mem0)  ←→  (proactive pre-loading)
```

## API

- `POST /chat` — Send a message (with memory-augmented response)
- `GET /memories/{user_id}` — List all memories
- `POST /reflect/{user_id}` — Trigger memory consolidation
- `DELETE /memories/{memory_id}` — Delete a memory
- `DELETE /memories/user/{user_id}` — Delete all user memories

## Stack

| Component | Technology |
|-----------|-----------|
| Agent Framework | Google ADK |
| Memory Layer | Mem0 |
| Vector Store | Qdrant |
| Graph Store | Neo4j (optional) |
| LLM | Gemini / Ollama / OpenAI |
| API | FastAPI |

## License

Apache 2.0
