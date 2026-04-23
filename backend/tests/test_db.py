"""Catalog database bootstrap tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pyromind.config import Settings


def test_init_db_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Running schema DDL twice on the same file must not error."""
    from pyromind.catalog.db import get_connection, init_db

    monkeypatch.setattr(
        "pyromind.config.settings",
        Settings(
            db_path=str(tmp_path / "idempotent.sqlite"),
            llm_provider="openrouter",
            openrouter_api_key="x",
        ),
    )
    conn = get_connection()
    try:
        init_db(conn)
        init_db(conn)
        conn.commit()
    finally:
        conn.close()


def test_seed_populates_50_effects(client: TestClient) -> None:
    """Startup seed must insert exactly 50 generic effects."""
    response = client.get("/effects", params={"limit": 200, "offset": 0})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 50
    assert len(body["items"]) == 50


def test_provenance_columns_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Effects table must expose provenance fields required by the product spec."""
    from pyromind.catalog.db import get_connection, init_db
    from pyromind.catalog.seeder import seed_if_empty

    monkeypatch.setattr(
        "pyromind.config.settings",
        Settings(
            db_path=str(tmp_path / "prov.sqlite"),
            llm_provider="openrouter",
            openrouter_api_key="x",
        ),
    )
    conn = get_connection()
    try:
        init_db(conn)
        seed_if_empty(conn)
        conn.commit()
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(effects)").fetchall()}
    finally:
        conn.close()
    for required in (
        "source",
        "license",
        "provenance_url",
        "redistributable",
        "vdl_params_json",
    ):
        assert required in cols
