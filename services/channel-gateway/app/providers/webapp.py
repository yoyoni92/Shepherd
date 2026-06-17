from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from shepherd_contracts import Channel, ChannelProvider, FileRef, IngestionPayload, MsgType, Sender


class WebappProvider(ChannelProvider):
    channel_id = "webapp"

    def verify_inbound(self, request: Any) -> bool:
        return True

    def parse_inbound(self, request: Any) -> IngestionPayload:
        """request keys: phone, display_name; for files: s3_key, mime, original_name; for text: text."""
        received_ts = request.get("received_ts") or datetime.now(UTC)
        sender = Sender(phone=request["phone"], display_name=request.get("display_name"))

        if "s3_key" in request:
            return IngestionPayload(
                channel=Channel.webapp,
                sender=sender,
                type=MsgType.file,
                file=FileRef(
                    s3_key=request["s3_key"],
                    mime=request.get("mime", "application/octet-stream"),
                    original_name=request.get("original_name"),
                ),
                received_ts=received_ts,
            )

        return IngestionPayload(
            channel=Channel.webapp,
            sender=sender,
            type=MsgType.text_command,
            text=request["text"],
            received_ts=received_ts,
        )

    def download_media(self, ref: Any) -> bytes:
        # ponytail: webapp bytes arrive in-band via multipart; this path is unused
        raise NotImplementedError("webapp media arrives in-band via multipart upload")

    def send_message(self, recipient: str, text: str, attachments: list | None = None) -> None:
        # ponytail: webapp has no push channel; alerts delivered via admin dashboard
        pass
