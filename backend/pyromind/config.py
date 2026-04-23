"""Application settings loaded from environment and optional `.env` file."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """PyroMind backend configuration."""

    llm_provider: Literal["openrouter", "ollama", "anthropic"] = "openrouter"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "qwen/qwen-2.5-72b-instruct"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:32b-instruct-q5_K_M"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    llm_temperature: float = 0.7
    llm_seed: int = 42
    llm_max_tokens: int = 4096
    db_path: str = "pyromind.sqlite"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def sqlite_path(self) -> Path:
        """Resolve SQLite file path relative to the backend package root when not absolute."""
        path = Path(self.db_path)
        if path.is_absolute():
            return path
        return BASE_DIR / path


settings = Settings()
