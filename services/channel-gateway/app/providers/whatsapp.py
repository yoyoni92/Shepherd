from __future__ import annotations

from typing import Any

from shepherd_contracts import ChannelProvider, IngestionPayload


class WhatsAppProvider(ChannelProvider):
    """Interface-ready stub. Implement against WhatsApp Cloud API when business number is approved."""

    channel_id = "whatsapp"

    def verify_inbound(self, request: Any) -> bool:
        raise NotImplementedError

    def parse_inbound(self, request: Any) -> IngestionPayload:
        raise NotImplementedError

    def download_media(self, ref: Any) -> bytes:
        raise NotImplementedError

    def send_message(self, recipient: str, text: str, attachments: list | None = None) -> None:
        raise NotImplementedError
