"""FastAPI entrypoint for the PyroMind sidecar."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pyromind.api.effects import router as effects_router
from pyromind.api.projects import router as projects_router
from pyromind.api.shows import router as shows_router
from pyromind.api.ws import router as ws_router
from pyromind.catalog.db import get_connection, init_db
from pyromind.catalog.embedder import build_embeddings_if_empty
from pyromind.catalog.seeder import seed_if_empty
from pyromind.graph.runtime import init_graph_runtime, shutdown_graph_runtime
import pyromind.config as _pm_config

_log = logging.getLogger(__name__)


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
    # Ensure agent logs (e.g. [show_director]) appear when the sidecar is spawned by Tauri.
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(name)s | %(levelname)s | %(message)s",
        )
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger("pyromind").setLevel(logging.INFO)

    conn = get_connection()
    try:
        init_db(conn)
        seed_if_empty(conn)
        try:
            build_embeddings_if_empty(conn)
        except Exception as exc:  # noqa: BLE001 — startup must not abort sidecar
            _log.exception("Effect embedding build skipped: %s", exc)
        conn.commit()
    finally:
        conn.close()
    _validate_llm_config()
    await init_graph_runtime()
    yield
    await shutdown_graph_runtime()


app = FastAPI(title="PyroMind Sidecar", version="0.1.0", lifespan=lifespan)

# Tauri dev loads the UI from Vite (e.g. http://localhost:1420) while the sidecar
# binds http://127.0.0.1:<port>. Browsers treat that as cross-origin; without CORS,
# fetch("/health") from the webview fails and the UI shows "Sidecar Unreachable".
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "tauri://localhost",
        "https://tauri.localhost",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1):\d+$",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)
app.include_router(effects_router)
app.include_router(shows_router)
app.include_router(ws_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Return sidecar health status."""
    return {"status": "ok"}
