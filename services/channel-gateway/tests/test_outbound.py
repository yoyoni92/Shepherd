"""T8 - Outbound send routes via recipient's channel provider."""
import re
from unittest.mock import patch

import httpx
import respx

from shepherd_contracts import Channel, IngestionPayload, MsgType, Sender


_TG_BASE = re.compile(r"https://api\.telegram\.org/bot[^/]+/sendMessage")


@respx.mock
def test_send_routes_via_registry_to_telegram(client):
    tg_send = respx.post(_TG_BASE).mock(
        return_value=httpx.Response(200, json={"ok": True})
    )

    response = client.post(
        "/send",
        json={"channel_id": "telegram", "recipient": "987654321", "text": "Maintenance due!"},
    )

    assert response.status_code == 200
    assert tg_send.called


def test_send_unknown_channel_returns_400(client):
    response = client.post(
        "/send",
        json={"channel_id": "carrier_pigeon", "recipient": "123", "text": "hello"},
    )
    assert response.status_code == 400


def test_registry_send_function_dispatches():
    from unittest.mock import MagicMock
    from app import registry
    from shepherd_contracts import ChannelProvider

    mock_provider = MagicMock(spec=ChannelProvider)
    mock_provider.channel_id = "test_ch"
    registry.register(mock_provider)

    registry.send("test_ch", "recipient_id", "hello", None)
    mock_provider.send_message.assert_called_once_with("recipient_id", "hello", None)
