"""Environment-backed settings for the Telegram bot."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from shepherd_config import get_config


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Telegram
    telegram_bot_token: str = ""
    telegram_bot_username: str = "ShepherdBot"

    # Fleet API (sole tool layer)
    fleet_api_url: str = "http://fleet-api:8000"
    internal_service_token: str = "change-me"

    # bot_sessions store
    database_url: str = ""

    # LLM touches
    openai_api_key: str = ""  # Whisper STT (accident description)
    gemini_api_key: str = ""  # Gemini vision (admin doc scan)


settings = Settings()


def _apply_shared_config(s: Settings) -> None:
    """Overlay shared config values onto *s*; no-op when config.toml is absent."""
    try:
        cfg = get_config()
    except FileNotFoundError:
        return
    s.database_url = cfg.database.url
    s.fleet_api_url = cfg.services.fleet_api_url


_apply_shared_config(settings)
