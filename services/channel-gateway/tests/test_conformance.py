"""T1 - Provider interface contract + registry."""
from datetime import UTC, datetime

import pytest

from shepherd_contracts import Channel, ChannelProvider, IngestionPayload, MsgType, Sender


class FakeProvider(ChannelProvider):
    channel_id = "fake"

    def verify_inbound(self, request) -> bool:
        return True

    def parse_inbound(self, request) -> IngestionPayload:
        return IngestionPayload(
            channel=Channel.telegram,
            sender=Sender(phone="+1234567890"),
            type=MsgType.text_command,
            text="hello",
            received_ts=datetime.now(UTC),
        )

    def download_media(self, ref) -> bytes:
        return b""

    def send_message(self, recipient, text, attachments=None) -> None:
        pass


def test_fake_provider_satisfies_interface():
    p = FakeProvider()
    assert p.channel_id == "fake"
    assert callable(p.verify_inbound)
    assert callable(p.parse_inbound)
    assert callable(p.download_media)
    assert callable(p.send_message)
    assert isinstance(p.parse_inbound({}), IngestionPayload)


def test_registry_register_and_get():
    from app.registry import get, register

    register(FakeProvider())
    provider = get("fake")
    assert isinstance(provider, ChannelProvider)
    assert provider.channel_id == "fake"


def test_registry_missing_channel_raises():
    from app.registry import get

    with pytest.raises(KeyError, match="nonexistent_xyz"):
        get("nonexistent_xyz")
