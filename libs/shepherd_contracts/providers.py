"""Swappable provider interfaces (channel, document extraction, guardrails)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .documents import DocType, ExtractionResult
from .ingestion import IngestionPayload


class ChannelProvider(ABC):
    """Bidirectional channel adapter. Implement + register to add a provider."""

    channel_id: str

    @abstractmethod
    def verify_inbound(self, request: Any) -> bool: ...

    @abstractmethod
    def parse_inbound(self, request: Any) -> IngestionPayload: ...

    @abstractmethod
    def download_media(self, ref: Any) -> bytes: ...

    @abstractmethod
    def send_message(self, recipient: str, text: str, attachments: list | None = None) -> None: ...


class DocumentExtractor(ABC):
    """PDF/image -> typed fields. Bedrock primary, Gemini fallback."""

    @abstractmethod
    def extract(self, s3_key: str, doc_type: DocType) -> ExtractionResult: ...


class GuardrailProvider(ABC):
    """Input + output rails."""

    @abstractmethod
    def check_input(self, text: str, context: Any) -> dict: ...

    @abstractmethod
    def check_output(self, text: str, sources: Any) -> dict: ...
