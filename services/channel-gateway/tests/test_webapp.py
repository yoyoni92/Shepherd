"""T7 - Webapp adapter parity with Telegram (shared assertion)."""
from datetime import UTC, datetime

from shepherd_contracts import Channel, MsgType


_SHARED_TS = datetime(2026, 6, 17, 12, 0, 0, tzinfo=UTC)
_PHONE = "+972501234567"
_S3_KEY = "inbox/webapp/+972501234567/20260617T120000Z.pdf"
_MIME = "application/pdf"
_ORIGINAL = "insurance.pdf"


def _tg_file_payload():
    from app.providers.telegram import TelegramProvider

    update = {
        "update_id": 10,
        "message": {
            "message_id": 10,
            "from": {"id": 111, "first_name": "John"},
            "chat": {"id": 111, "type": "private"},
            "date": int(_SHARED_TS.timestamp()),
            "document": {"file_id": "doc_id", "file_name": _ORIGINAL, "mime_type": _MIME},
        },
    }
    req = {"update": update, "phone": _PHONE, "s3_key": _S3_KEY, "mime": _MIME}
    return TelegramProvider().parse_inbound(req)


def _webapp_file_payload():
    from app.providers.webapp import WebappProvider

    req = {
        "phone": _PHONE,
        "s3_key": _S3_KEY,
        "mime": _MIME,
        "original_name": _ORIGINAL,
        "received_ts": _SHARED_TS,
    }
    return WebappProvider().parse_inbound(req)


def test_webapp_file_payload_structure_matches_telegram():
    tg = _tg_file_payload()
    wa = _webapp_file_payload()

    assert tg.type == wa.type == MsgType.file
    assert tg.file is not None and wa.file is not None
    assert tg.file.s3_key == wa.file.s3_key == _S3_KEY
    assert tg.file.mime == wa.file.mime == _MIME
    assert tg.file.original_name == wa.file.original_name == _ORIGINAL
    assert tg.sender.phone == wa.sender.phone == _PHONE


def test_webapp_text_payload_structure():
    from app.providers.webapp import WebappProvider

    req = {"phone": _PHONE, "text": "log km 86500", "received_ts": _SHARED_TS}
    payload = WebappProvider().parse_inbound(req)

    assert payload.type == MsgType.text_command
    assert payload.channel == Channel.webapp
    assert payload.text == "log km 86500"
    assert payload.sender.phone == _PHONE


def test_webapp_multipart_endpoint_produces_file_payload(client):
    import io
    from unittest.mock import patch

    import boto3
    from moto import mock_aws

    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")

        captured: list = []

        async def fake_forward(payload):
            captured.append(payload)

        with patch("app.main.ingest.forward", side_effect=fake_forward):
            response = client.post(
                "/webapp/ingest",
                data={"phone": _PHONE},
                files={"file": ("insurance.pdf", io.BytesIO(b"PDF"), "application/pdf")},
            )

    assert response.status_code == 200
    assert len(captured) == 1
    payload = captured[0]
    assert payload.type == MsgType.file
    assert payload.channel == Channel.webapp
    assert payload.sender.phone == _PHONE
    assert payload.file is not None
    assert "inbox/webapp/" in payload.file.s3_key
