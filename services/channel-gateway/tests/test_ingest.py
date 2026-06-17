"""T6 - Forward to n8n (respx mock)."""
import re
from datetime import UTC, datetime

import boto3
import httpx
import pytest
import respx
from moto import mock_aws

from shepherd_contracts import Channel, FileRef, IngestionPayload, MsgType, Sender

_N8N_URL = "http://n8n-test/webhook/ingest"

_PAYLOAD = IngestionPayload(
    channel=Channel.telegram,
    sender=Sender(phone="+972501234567", display_name="John"),
    type=MsgType.text_command,
    text="log km 86500",
    received_ts=datetime(2026, 6, 17, 12, 0, 0, tzinfo=UTC),
)

_FILE_PAYLOAD = IngestionPayload(
    channel=Channel.telegram,
    sender=Sender(phone="+972501234567"),
    type=MsgType.file,
    file=FileRef(s3_key="inbox/telegram/123/20260617T000000Z.jpg", mime="image/jpeg"),
    received_ts=datetime(2026, 6, 17, 12, 0, 0, tzinfo=UTC),
)


@respx.mock
@pytest.mark.asyncio
async def test_forward_posts_normalized_payload():
    from app.ingest import forward

    n8n = respx.post(_N8N_URL).mock(return_value=httpx.Response(200, json={"ok": True}))

    await forward(_PAYLOAD)

    assert n8n.called
    body = n8n.calls.last.request.content
    import json
    data = json.loads(body)
    assert data["channel"] == "telegram"
    assert data["sender"]["phone"] == "+972501234567"
    assert data["type"] == "text_command"
    assert data["text"] == "log km 86500"


@respx.mock
@pytest.mark.asyncio
async def test_forward_raises_on_4xx():
    from app.ingest import forward

    respx.post(_N8N_URL).mock(return_value=httpx.Response(400, json={"error": "bad request"}))

    with pytest.raises(httpx.HTTPStatusError):
        await forward(_PAYLOAD)


@respx.mock
@pytest.mark.asyncio
async def test_forward_includes_s3_key_for_file_payload():
    from app.ingest import forward

    n8n = respx.post(_N8N_URL).mock(return_value=httpx.Response(200, json={"ok": True}))

    await forward(_FILE_PAYLOAD)

    import json
    data = json.loads(n8n.calls.last.request.content)
    assert data["type"] == "file"
    assert data["file"]["s3_key"] == "inbox/telegram/123/20260617T000000Z.jpg"


@mock_aws
def test_put_s3_uploads_object():
    from app.ingest import put_s3

    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-bucket")

    put_s3("inbox/test/file.pdf", b"PDF_BYTES", "application/pdf")

    obj = s3.get_object(Bucket="test-bucket", Key="inbox/test/file.pdf")
    assert obj["Body"].read() == b"PDF_BYTES"
    assert obj["ContentType"] == "application/pdf"
