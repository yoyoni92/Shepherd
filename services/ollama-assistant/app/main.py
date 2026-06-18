"""Ollama assistant FastAPI service - /chat endpoint."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.assistant import ask

app = FastAPI(title="Shepherd Ollama Assistant", version="0.1.0")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    content: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        content = ask(req.message)
        return ChatResponse(content=content)
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
