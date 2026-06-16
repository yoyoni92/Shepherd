"""Shared contracts for Shepherd services."""
from .auth import CallerContext, Role
from .documents import (
    DocType,
    ExtractionResult,
    InsuranceFields,
    LicenseFields,
    TicketFields,
)
from .ingestion import Channel, FileRef, IngestionPayload, MsgType, Sender
from .providers import ChannelProvider, DocumentExtractor, GuardrailProvider

__all__ = [
    "Channel",
    "MsgType",
    "Sender",
    "FileRef",
    "IngestionPayload",
    "Role",
    "CallerContext",
    "DocType",
    "InsuranceFields",
    "LicenseFields",
    "TicketFields",
    "ExtractionResult",
    "ChannelProvider",
    "DocumentExtractor",
    "GuardrailProvider",
]
