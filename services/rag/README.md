# rag

Semantic Q&A grounded in vehicle-profile docs synced from Postgres.
Prompt-engineering surface #3.

Stack: FastAPI, ChromaDB, `paraphrase-multilingual-MiniLM-L12-v2` (local embeddings),
LangChain. Generation is Anthropic Claude at runtime; Llama.cpp is used only by the
offline eval `--live` path (see below).

## Setup

```bash
poetry env use python3.12
poetry install
```

## Required env vars

| Var | Description |
|-----|-------------|
| `DATABASE_URL` | Read-only Postgres URL (uses `rag_readonly` role) |
| `ANTHROPIC_API_KEY` | Anthropic key - generation at runtime |
| `ANTHROPIC_MODEL` | Generation model (default: `claude-sonnet-4-6`) |
| `LLAMA_MODEL_PATH` | Only for `eval.run --live`: absolute path to a GGUF model file |

## Run

```bash
uvicorn app.main:app --port 8000   # compose publishes this on host port 8004
```

## Test

```bash
poetry run pytest tests/ -m "not live"
```

## Eval harness (prompt quality)

```bash
poetry run python -m eval.run           # mock LLM (offline)
poetry run python -m eval.run --live    # real Llama.cpp (needs LLAMA_MODEL_PATH)
```

Results are appended to `eval/prompt_log.md`. Current V5: 12/12 (100%).

## Endpoints

- `POST /query` - `{question, caller_context}` -> `{answer, citations[]}`
- `GET /health`

## Sync

Bulk-index on startup or cron:

```python
from app.sync import bulk
bulk(session, collection)
```

Re-embed a single vehicle after a Fleet API write:

```python
from app.sync import upsert
upsert(session, collection, vehicle_id)
```
