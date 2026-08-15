from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./trixlog.db"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"
    environment: str = "development"

    # Cost Allocation Engine — Camada 2
    camada2_max_dias_janela: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
