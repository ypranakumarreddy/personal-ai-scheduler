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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()

