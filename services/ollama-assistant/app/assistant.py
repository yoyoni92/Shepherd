"""Ollama client + system prompt. No Fleet API / RAG imports - DB-blind by design."""
import os
from pathlib import Path

import httpx


def ask(text: str) -> str:
    # Read env vars at call time so tests can override without module re-import.
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    model = os.environ.get("OLLAMA_MODEL", "llama3")
    prompt_path = os.environ.get("SYSTEM_PROMPT_PATH", "/prompts/ollama_system.txt")
    timeout = float(os.environ.get("OLLAMA_TIMEOUT", "30"))
    system_prompt = Path(prompt_path).read_text()
    try:
        resp = httpx.post(
            f"{url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                "stream": False,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]
    except httpx.TimeoutException as e:
        raise TimeoutError(f"Ollama timed out after {timeout}s") from e
