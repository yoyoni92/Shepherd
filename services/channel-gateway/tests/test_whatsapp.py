"""T9 - WhatsApp stub satisfies interface but raises NotImplementedError on all calls."""
import pytest

from shepherd_contracts import ChannelProvider


def test_whatsapp_provider_satisfies_interface():
    from app.providers.whatsapp import WhatsAppProvider

    provider = WhatsAppProvider()
    assert isinstance(provider, ChannelProvider)
    assert provider.channel_id == "whatsapp"
    assert callable(provider.verify_inbound)
    assert callable(provider.parse_inbound)
    assert callable(provider.download_media)
    assert callable(provider.send_message)


def test_whatsapp_verify_inbound_raises():
    from app.providers.whatsapp import WhatsAppProvider

    with pytest.raises(NotImplementedError):
        WhatsAppProvider().verify_inbound({})


def test_whatsapp_parse_inbound_raises():
    from app.providers.whatsapp import WhatsAppProvider

    with pytest.raises(NotImplementedError):
        WhatsAppProvider().parse_inbound({})


def test_whatsapp_download_media_raises():
    from app.providers.whatsapp import WhatsAppProvider

    with pytest.raises(NotImplementedError):
        WhatsAppProvider().download_media("ref")


def test_whatsapp_send_message_raises():
    from app.providers.whatsapp import WhatsAppProvider

    with pytest.raises(NotImplementedError):
        WhatsAppProvider().send_message("recipient", "text")
