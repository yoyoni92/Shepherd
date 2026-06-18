# rag

Semantic Q&A grounded in vehicle-profile docs synced from Postgres.
Prompt-engineering surface #3.

Stack: FastAPI, ChromaDB, `paraphrase-multilingual-MiniLM-L12-v2`, LangChain, Llama.cpp.

## Setup

```bash
poetry env use python3.12
poetry install
```

## Required env vars

| Var | Description |
|-----|-------------|
| `DATABASE_URL` | Read-only Postgres URL (uses `rag_readonly` role) |
| `LLAMA_MODEL_PATH` | Absolute path to a GGUF model file |

## Run

```bash
uvicorn app.main:app --port 8003
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
