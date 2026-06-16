"""Normalized ingestion payload - the one contract every channel produces."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, model_validator


class Channel(str, Enum):
    telegram = "telegram"
    whatsapp = "whatsapp"
    webapp = "webapp"


class MsgType(str, Enum):
    file = "file"
    text_command = "text_command"


class Sender(BaseModel):
    phone: str
    display_name: str | None = None


class FileRef(BaseModel):
    s3_key: str
    mime: str
    original_name: str | None = None


class IngestionPayload(BaseModel):
    channel: Channel
    sender: Sender
    type: MsgType
    file: FileRef | None = None
    text: str | None = None
    plate_hint: str | None = None
    received_ts: datetime

    @model_validator(mode="after")
    def _consistent_payload(self) -> IngestionPayload:
        if self.type is MsgType.file and self.file is None:
            raise ValueError("file payload requires `file`")
        if self.type is MsgType.text_command and not self.text:
            raise ValueError("text_command payload requires `text`")
        return self
