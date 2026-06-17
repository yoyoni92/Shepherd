from __future__ import annotations

from shepherd_contracts import ChannelProvider

_registry: dict[str, ChannelProvider] = {}


def register(provider: ChannelProvider) -> None:
    _registry[provider.channel_id] = provider


def get(channel_id: str) -> ChannelProvider:
    try:
        return _registry[channel_id]
    except KeyError:
        raise KeyError(f"No provider for channel: {channel_id!r}")


def send(channel_id: str, recipient: str, text: str, attachments: list | None = None) -> None:
    get(channel_id).send_message(recipient, text, attachments)
