"""sqlite-vec insert + search (no sentence-transformers)."""

from __future__ import annotations

import json
import random

import pytest

from pyromind.catalog import vectors as vec_mod
from pyromind.catalog.db import get_connection, init_db
from pyromind.config import Settings


def _patch_db(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
    import pyromind.config as cfg

    monkeypatch.setattr(
        cfg,
        "settings",
        Settings(
            db_path=str(tmp_path / "vec.sqlite"),
            projects_dir=str(tmp_path / "proj"),
            openrouter_api_key="x",
            audio_device="cpu",
        ),
    )


def _insert_effect(conn: object, eid: str, *, family: str = "shell", caliber: int = 3) -> None:
    conn.execute(
        """
        INSERT INTO effects (
            id, name, family, caliber_in, colors, duration_s, height_m,
            burst_radius_m, prefire_ms, lift_time_ms, sound_level,
            recommended_use, description, vdl_params_json, source, license,
            provenance_url, redistributable
        ) VALUES (?, ?, ?, ?, ?, 4.0, 80.0, 20.0, 500, 500, 'medium', '',
        'desc', NULL, 'test', 'CC0', NULL, 1)
        """,
        (eid, f"Effect {eid}", family, caliber, json.dumps(["red"])),
    )


def test_insert_and_search(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
    _patch_db(monkeypatch, tmp_path)
    conn = get_connection()
    init_db(conn)
    rng = random.Random(42)
    ids: list[str] = []
    embeddings: list[list[float]] = []
    for i in range(5):
        eid = f"vec-{i}"
        ids.append(eid)
        emb = [rng.random() for _ in range(1024)]
        embeddings.append(emb)
        _insert_effect(conn, eid)
        vec_mod.insert_embedding(conn, eid, emb)
    conn.commit()

    target = embeddings[2]
    hits = vec_mod.search_similar(conn, target, limit=10, knn_pool=50)
    conn.close()
    assert hits, "expected KNN hits"
    best_id, best_dist = hits[0]
    assert best_id == ids[2]
    assert best_dist == min(d for _, d in hits)


def test_filters_applied(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
    _patch_db(monkeypatch, tmp_path)
    conn = get_connection()
    init_db(conn)
    v = [0.02] * 1024
    v[0] = 1.0
    _insert_effect(conn, "a1", family="shell", caliber=3)
    _insert_effect(conn, "a2", family="comet", caliber=3)
    vec_mod.insert_embedding(conn, "a1", v)
    vec_mod.insert_embedding(conn, "a2", v)
    conn.commit()

    hits = vec_mod.search_similar(conn, v, limit=10, filters={"family": "shell"})
    conn.close()
    assert [h[0] for h in hits] == ["a1"]
