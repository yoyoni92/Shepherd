from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from shepherd_contracts import Channel, FileRef, IngestionPayload, MsgType, Sender

NOW = datetime(2026, 6, 16, tzinfo=UTC)


def _sender() -> Sender:
    return Sender(phone="+972500000000", display_name="Driver D")


def test_valid_file_payload():
    p = IngestionPayload(
        channel=Channel.telegram,
        sender=_sender(),
        type=MsgType.file,
        file=FileRef(s3_key="vehicles/x/insurance/1.pdf", mime="application/pdf"),
        received_ts=NOW,
    )
    assert p.channel is Channel.telegram
    assert p.file is not None


def test_valid_text_command():
    p = IngestionPayload(
        channel=Channel.webapp,
        sender=_sender(),
        type=MsgType.text_command,
        text="log km 86500 for 12-345-67",
        received_ts=NOW,
    )
    assert p.text


def test_file_payload_requires_file():
    with pytest.raises(ValidationError):
        IngestionPayload(
            channel=Channel.telegram, sender=_sender(), type=MsgType.file, received_ts=NOW
        )


def test_text_command_requires_text():
    with pytest.raises(ValidationError):
        IngestionPayload(
            channel=Channel.telegram, sender=_sender(), type=MsgType.text_command, received_ts=NOW
        )


def test_invalid_channel_rejected():
    with pytest.raises(ValidationError):
        IngestionPayload(
            channel="carrier-pigeon", sender=_sender(), type=MsgType.text_command,
            text="hi", received_ts=NOW,
        )
