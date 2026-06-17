from __future__ import annotations

from pydantic import BaseModel


class SendRequest(BaseModel):
    channel_id: str
    recipient: str
    text: str
    attachments: list[str] | None = None
