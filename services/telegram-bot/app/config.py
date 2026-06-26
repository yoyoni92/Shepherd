"""Environment-backed settings for the Telegram bot."""

from pydantic_settings import BaseSettings, SettingsConfigDict


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
