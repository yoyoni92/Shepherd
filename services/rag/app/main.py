import os

from fastapi import FastAPI
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel

from app.generate import answer
from app.retrieve import query

app = FastAPI(title="Shepherd RAG Service", version="0.1.0")

# ponytail: lazy singletons - no startup overhead for tests; set in tests via dependency override
_collection = None
_llm = None


def _get_collection():
    global _collection
    if _collection is None:
        import chromadb
        from app.embed import get_chroma_ef
        client = chromadb.EphemeralClient()
        _collection = client.get_or_create_collection("vehicles", embedding_function=get_chroma_ef())
    return _collection


def _get_llm():
    global _llm
    if _llm is None:
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        llm = ChatAnthropic(model=model, temperature=0, max_tokens=512)
        _llm = lambda prompt: llm.invoke(prompt).content
    return _llm


class QueryRequest(BaseModel):
    question: str
    caller_context: dict


class QueryResponse(BaseModel):
    answer: str
    citations: list[str]


@app.post("/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest) -> QueryResponse:
    retrieved = query(_get_collection(), req.question, req.caller_context)
    result = answer(req.question, retrieved, _get_llm())
    return QueryResponse(**result)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
