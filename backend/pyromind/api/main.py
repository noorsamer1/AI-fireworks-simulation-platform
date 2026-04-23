"""FastAPI entrypoint for the PyroMind sidecar."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from pyromind.api.effects import router as effects_router
from pyromind.api.projects import router as projects_router
from pyromind.catalog.db import get_connection, init_db
from pyromind.catalog.seeder import seed_if_empty
import pyromind.config as _pm_config


def _validate_llm_config() -> None:
    """Fail fast when OpenRouter is selected without credentials."""
    s_cfg = _pm_config.settings
    if s_cfg.llm_provider == "openrouter" and not s_cfg.openrouter_api_key.strip():
        raise RuntimeError(
            "OPENROUTER_API_KEY is empty while LLM_PROVIDER=openrouter. "
            "Set the key in backend/.env or switch LLM_PROVIDER (e.g. to ollama)."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize SQLite, seed catalog, rebuild FTS, and validate LLM settings."""
    conn = get_connection()
    try:
        init_db(conn)
        seed_if_empty(conn)
        conn.commit()
    finally:
        conn.close()
    _validate_llm_config()
    yield


app = FastAPI(title="PyroMind Sidecar", version="0.1.0", lifespan=lifespan)
app.include_router(projects_router)
app.include_router(effects_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Return sidecar health status."""
    return {"status": "ok"}
