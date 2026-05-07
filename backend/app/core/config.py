from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Personal AI Scheduler"
    app_env: str = "development"
    database_url: str = "sqlite:///./scheduler.db"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    enable_calendar_sync: bool = False
    default_timezone: str = "America/Chicago"
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
