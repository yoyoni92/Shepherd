"""T3 - Telegram text inbound + contact-share; T4 - Telegram file -> S3."""
import re
from unittest.mock import patch

import boto3
import httpx
import pytest
import respx
from moto import mock_aws

from shepherd_contracts import Channel, IngestionPayload, MsgType

_TEXT_UPDATE = {
    "update_id": 1,
    "message": {
        "message_id": 1,
        "from": {"id": 987654321, "first_name": "John"},
        "chat": {"id": 987654321, "type": "private"},
        "date": 1718500000,
        "text": "hello world",
    },
}

_PHOTO_UPDATE = {
    "update_id": 2,
    "message": {
        "message_id": 2,
        "from": {"id": 987654321, "first_name": "John"},
        "chat": {"id": 987654321, "type": "private"},
        "date": 1718500000,
        "photo": [
            {"file_id": "small_id", "file_unique_id": "s1", "file_size": 1000, "width": 100, "height": 100},
            {"file_id": "large_id", "file_unique_id": "s2", "file_size": 50000, "width": 800, "height": 600},
        ],
    },
}

_CONTACT_UPDATE = {
    "update_id": 3,
    "message": {
        "message_id": 3,
        "from": {"id": 987654321, "first_name": "John"},
        "chat": {"id": 987654321, "type": "private"},
        "date": 1718500000,
        "contact": {"phone_number": "+972501234567", "first_name": "John"},
    },
}

_TG_BASE = re.compile(r"https://api\.telegram\.org/bot[^/]+/.*")


# --- T3: parse_inbound unit ---

def test_parse_text_returns_payload():
    from app.providers.telegram import TelegramProvider

    provider = TelegramProvider()
    req = {"update": _TEXT_UPDATE, "phone": "+972501234567", "display_name": "John"}
    payload = provider.parse_inbound(req)

    assert isinstance(payload, IngestionPayload)
    assert payload.channel == Channel.telegram
    assert payload.type == MsgType.text_command
    assert payload.text == "hello world"
    assert payload.sender.phone == "+972501234567"


def test_parse_photo_returns_file_payload():
    from app.providers.telegram import TelegramProvider

    provider = TelegramProvider()
    req = {
        "update": _PHOTO_UPDATE,
        "phone": "+972501234567",
        "s3_key": "inbox/telegram/987654321/20260617T000000Z.jpg",
        "mime": "image/jpeg",
    }
    payload = provider.parse_inbound(req)

    assert payload.type == MsgType.file
    assert payload.file is not None
    assert payload.file.s3_key == "inbox/telegram/987654321/20260617T000000Z.jpg"
    assert payload.file.mime == "image/jpeg"


# --- T3: endpoint - unknown chat triggers contact-share ---

@respx.mock
def test_unknown_chat_triggers_contact_share(client, mock_db):
    mock_db.query.return_value.filter_by.return_value.first.return_value = None

    tg_send = respx.post(_TG_BASE).mock(return_value=httpx.Response(200, json={"ok": True}))

    response = client.post("/telegram/webhook", json=_TEXT_UPDATE)

    assert response.status_code == 200
    assert tg_send.called


# --- T3: endpoint - contact share message binds identity ---

@respx.mock
def test_contact_share_binds_identity(client, mock_db):
    mock_db.query.return_value.filter_by.return_value.first.return_value = None
    respx.post(_TG_BASE).mock(return_value=httpx.Response(200, json={"ok": True}))

    with patch("app.main.identity.bind") as mock_bind:
        response = client.post("/telegram/webhook", json=_CONTACT_UPDATE)

    assert response.status_code == 200
    mock_bind.assert_called_once_with(
        "telegram", "987654321", "+972501234567", mock_db
    )


# --- T4: download_media calls getFile then downloads ---

@respx.mock
def test_download_media_calls_get_file_and_fetches_bytes():
    from app.providers.telegram import TelegramProvider

    respx.get(re.compile(r".*/getFile.*")).mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"file_path": "docs/file.jpg"}})
    )
    respx.get(re.compile(r".*/file/.*")).mock(
        return_value=httpx.Response(200, content=b"JPEG_BYTES")
    )

    provider = TelegramProvider()
    data = provider.download_media("large_id")
    assert data == b"JPEG_BYTES"


# --- T4: endpoint - photo update -> S3 upload, payload has s3_key ---

@mock_aws
@respx.mock
def test_photo_endpoint_uploads_to_s3_and_payload_has_key(client, mock_db):
    # Identity resolves phone
    from unittest.mock import MagicMock
    from shepherd_db.models import ChannelStatusEnum
    row = MagicMock()
    row.phone_number = "+972501234567"
    row.status = ChannelStatusEnum.linked
    mock_db.query.return_value.filter_by.return_value.first.return_value = row

    # Create S3 bucket
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-bucket")

    # Mock Telegram getFile + download
    respx.get(re.compile(r".*/getFile.*")).mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"file_path": "photos/abc.jpg"}})
    )
    respx.get(re.compile(r".*/file/.*")).mock(
        return_value=httpx.Response(200, content=b"JPEG_BYTES")
    )

    # Mock n8n forward
    captured: list = []

    async def fake_forward(payload):
        captured.append(payload)

    with patch("app.main.ingest.forward", side_effect=fake_forward):
        response = client.post("/telegram/webhook", json=_PHOTO_UPDATE)

    assert response.status_code == 200
    assert len(captured) == 1

    payload = captured[0]
    assert payload.type == MsgType.file
    assert payload.file is not None
    assert "inbox/telegram/987654321/" in payload.file.s3_key
    assert payload.file.mime == "image/jpeg"

    # Verify object is in S3
    objects = s3.list_objects_v2(Bucket="test-bucket")
    keys = [o["Key"] for o in objects.get("Contents", [])]
    assert any("inbox/telegram/987654321/" in k for k in keys)
