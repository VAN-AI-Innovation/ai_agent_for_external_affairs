from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    ai_provider: str = Field(default="auto", alias="AI_PROVIDER")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5.6-luna", alias="OPENAI_MODEL")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_timeout_seconds: int = Field(default=60, alias="OPENAI_TIMEOUT_SECONDS")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta",
        alias="GEMINI_BASE_URL",
    )
    gemini_timeout_seconds: int = Field(default=60, alias="GEMINI_TIMEOUT_SECONDS")
    local_model_id: str = Field(default="Qwen/Qwen2.5-0.5B-Instruct", alias="LOCAL_MODEL_ID")
    local_model_max_new_tokens: int = Field(default=700, alias="LOCAL_MODEL_MAX_NEW_TOKENS")
    web_research_enabled: bool = Field(default=True, alias="WEB_RESEARCH_ENABLED")
    web_research_provider: str = Field(default="auto", alias="WEB_RESEARCH_PROVIDER")
    web_research_timeout_seconds: int = Field(default=4, alias="WEB_RESEARCH_TIMEOUT_SECONDS")
    web_research_max_sources: int = Field(default=3, alias="WEB_RESEARCH_MAX_SOURCES")
    database_url: str = Field(default="sqlite:///./data/app.db", alias="DATABASE_URL")
    app_env: str = Field(default="local", alias="APP_ENV")
    backend_cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:5175,http://127.0.0.1:5175",
        alias="BACKEND_CORS_ORIGINS",
    )

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
