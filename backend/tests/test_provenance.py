"""Provenance field round-trip tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_redistributable_false_roundtrip(client: TestClient) -> None:
    """User-authored effect can set redistributable to false and read it back."""
    body = {
        "name": "Private custom comet",
        "family": "comet",
        "colors": ["violet"],
        "duration_s": 2.0,
        "height_m": 40.0,
        "burst_radius_m": 5.0,
        "prefire_ms": 50,
        "lift_time_ms": 0,
        "source": "user_import:local-file",
        "license": "user_owned",
        "redistributable": False,
        "description": "Imported from a user-owned file.",
    }
    created = client.post("/effects", json=body)
    assert created.status_code == 201
    effect_id = created.json()["id"]
    assert created.json()["redistributable"] is False
    fetched = client.get(f"/effects/{effect_id}")
    assert fetched.json()["redistributable"] is False


def test_user_import_source_label(client: TestClient) -> None:
    """Custom source label survives persistence."""
    payload = {
        "name": "Mine sequence",
        "family": "mine",
        "colors": ["red"],
        "duration_s": 4.0,
        "height_m": 10.0,
        "burst_radius_m": 15.0,
        "prefire_ms": 100,
        "lift_time_ms": 0,
        "source": "user_import:show_folder_2026",
        "license": "user_owned",
        "description": "User import path encoded in source.",
    }
    row = client.post("/effects", json=payload).json()
    assert row["source"].startswith("user_import:")


def test_generative_source_label(client: TestClient) -> None:
    """Seeded rows remain generative with internal license."""
    first = client.get("/effects", params={"limit": 1}).json()["items"][0]
    assert first["source"] == "generative"
    assert first["license"] == "pyromind-internal"
