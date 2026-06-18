"""Factory for DocumentExtractor providers and shared error type."""
from __future__ import annotations

import os

from shepherd_contracts import DocumentExtractor


class ExtractionError(Exception):
    def __init__(self, message: str = "", *, reason: str = "unknown") -> None:
        super().__init__(message or reason)
        self.reason = reason


def get_extractor(provider: str | None = None) -> DocumentExtractor:
    """Return the configured extractor. Fails fast if required env vars are missing."""
    provider = (provider or os.environ.get("EXTRACTOR_PROVIDER", "bedrock")).lower()
    if provider == "gemini":
        from app.gemini import GeminiExtractor
        return GeminiExtractor()
    from app.bedrock import BedrockExtractor
    return BedrockExtractor()
