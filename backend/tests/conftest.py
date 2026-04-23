"""Pytest configuration for backend tests."""

from __future__ import annotations

import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Isolated SQLite file + dummy OpenRouter key for FastAPI tests."""
    from pyromind.config import Settings

    monkeypatch.setattr(
        "pyromind.config.settings",
        Settings(
            db_path=str(tmp_path / "test.sqlite"),
            llm_provider="openrouter",
            openrouter_api_key="sk-test-dummy",
        ),
    )
    from pyromind.api.main import app

    with TestClient(app) as test_client:
        yield test_client
