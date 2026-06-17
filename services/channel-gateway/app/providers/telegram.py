from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import httpx

from shepherd_contracts import Channel, ChannelProvider, FileRef, IngestionPayload, MsgType, Sender

_TG_API = "https://api.telegram.org"

CONTACT_SHARE_MSG = (
    "Hi! To use this service please share your phone number by pressing the button below."
)


def _token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "")


class TelegramProvider(ChannelProvider):
    channel_id = "telegram"

    def verify_inbound(self, request: Any) -> bool:
        # ponytail: no HMAC check; add X-Telegram-Bot-Api-Secret-Token validation for prod
        return True

    def parse_inbound(self, request: Any) -> IngestionPayload:
        """request keys: update, phone, display_name; for media also: s3_key, mime."""
        update = request["update"]
        msg = update["message"]
        phone: str = request["phone"]
        display_name: str | None = request.get("display_name")
        received_ts = datetime.fromtimestamp(msg.get("date", 0), tz=UTC)
        sender = Sender(phone=phone, display_name=display_name)

        if "photo" in msg or "document" in msg:
            original: str | None = None
            if "document" in msg:
                original = msg["document"].get("file_name")
            return IngestionPayload(
                channel=Channel.telegram,
                sender=sender,
                type=MsgType.file,
                file=FileRef(
                    s3_key=request["s3_key"],
                    mime=request.get("mime", "application/octet-stream"),
                    original_name=original,
                ),
                received_ts=received_ts,
            )

        return IngestionPayload(
            channel=Channel.telegram,
            sender=sender,
            type=MsgType.text_command,
            text=msg.get("text", ""),
            received_ts=received_ts,
        )

    def download_media(self, ref: Any) -> bytes:
        """ref: Telegram file_id string."""
        token = _token()
        with httpx.Client() as client:
            info = client.get(
                f"{_TG_API}/bot{token}/getFile", params={"file_id": ref}
            )
            info.raise_for_status()
            file_path = info.json()["result"]["file_path"]
            data = client.get(f"{_TG_API}/file/bot{token}/{file_path}")
            data.raise_for_status()
            return data.content

    def send_message(
        self, recipient: str, text: str, attachments: list | None = None
    ) -> None:
        token = _token()
        with httpx.Client() as client:
            client.post(
                f"{_TG_API}/bot{token}/sendMessage",
                json={"chat_id": recipient, "text": text},
            ).raise_for_status()

    def request_contact(self, chat_id: str) -> None:
        token = _token()
        with httpx.Client() as client:
            client.post(
                f"{_TG_API}/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": CONTACT_SHARE_MSG,
                    "reply_markup": {
                        "keyboard": [[{"text": "Share phone", "request_contact": True}]],
                        "one_time_keyboard": True,
                        "resize_keyboard": True,
                    },
                },
            ).raise_for_status()
