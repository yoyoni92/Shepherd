"""Normalized update context (`ctx`) - the single object every flow handler receives.

Flattens an aiogram message/callback into the same shape the n8n `Normalize` node
produced, plus the resolved `whoami` and the loaded `bot_sessions` state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.fleet import FleetClient


@dataclass
class Ctx:
    chat_id: int
    bot: Any  # aiogram Bot (AsyncMock in tests)
    fleet: FleetClient
    is_callback: bool = False
    callback_data: str | None = None
    command: str | None = None
    text: str | None = None
    voice_id: str | None = None
    photo_id: str | None = None
    video_id: str | None = None
    document_id: str | None = None
    document_name: str | None = None
    contact_phone: str | None = None
    contact_user_id: int | None = None
    sender_id: int | None = None
    is_start: bool = False
    start_token: str | None = None
    whoami: dict[str, Any] | None = None
    state: dict[str, Any] = field(default_factory=dict)

    @property
    def role(self) -> str | None:
        return self.whoami.get("role") if self.whoami else None

    @property
    def driver_id(self) -> str | None:
        return self.whoami.get("driver_id") if self.whoami else None

    @property
    def driver_name(self) -> str | None:
        return self.whoami.get("driver_name") if self.whoami else None

    @property
    def company_id(self) -> str | None:
        return self.whoami.get("company_id") if self.whoami else None

    @property
    def attendance_enabled(self) -> bool:
        """Whether the user's company has the attendance feature flag on (default off)."""
        return bool(self.whoami.get("attendance_enabled")) if self.whoami else False

    @property
    def flow(self) -> str | None:
        return self.state.get("flow")

    @property
    def step(self) -> str | None:
        return self.state.get("step")
