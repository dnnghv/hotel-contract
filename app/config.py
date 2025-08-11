from __future__ import annotations

from pydantic import BaseSettings, Field, AnyHttpUrl


class Settings(BaseSettings):
    docling_api_url: AnyHttpUrl = Field(..., alias="DOCLING_API_URL")
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    data_dir: str = Field("/home/ebk/AI.ROVI/Contract Test/data", alias="DATA_DIR")

    class Config:
        env_file = ".env"
        case_sensitive = True


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()  # will read from env/.env
    return _settings


def get_docling_url() -> str:
    return str(get_settings().docling_api_url)


def get_openai_key() -> str:
    return get_settings().openai_api_key


def get_data_dir(default: str | None = None) -> str:
    return get_settings().data_dir 