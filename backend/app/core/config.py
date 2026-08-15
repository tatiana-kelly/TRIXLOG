from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Ancorado em backend/ (não no cwd do processo) — uvicorn com --app-dir pode ser iniciado de
# qualquer diretório, e um caminho relativo "./trixlog.db"/".env" silenciosamente aponta pro
# lugar errado (ou falha) dependendo de onde o servidor foi lançado.
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), extra="ignore")

    database_url: str = f"sqlite:///{(BACKEND_DIR / 'trixlog.db').as_posix()}"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"
    environment: str = "development"

    # Cost Allocation Engine — Camada 2
    camada2_max_dias_janela: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
