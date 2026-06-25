"""Speech-to-text for the accident description (OpenAI Whisper, Hebrew)."""

from __future__ import annotations

from openai import AsyncOpenAI

from app.config import settings

_client: AsyncOpenAI | None = None


def _get() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def transcribe(audio: bytes, filename: str = "voice.ogg", language: str = "he") -> str:
    resp = await _get().audio.transcriptions.create(
        model="whisper-1", file=(filename, audio), language=language
    )
    return (resp.text or "").strip()
