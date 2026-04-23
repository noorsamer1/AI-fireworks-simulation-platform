"""EffectLibrarian agent tests (sqlite-vec + mocked embedder)."""

from __future__ import annotations

import json

import pytest

import pyromind.agents.effect_librarian as el_mod
from pyromind.catalog import vectors as vec_mod
from pyromind.catalog.db import get_connection, init_db
from pyromind.catalog.seeder import seed_if_empty
from pyromind.config import Settings
from pyromind.models.plan import Palette, PlanSection, ShowPlan
from pyromind.models.show import UserConstraints

from tests.graph_test_utils import minimal_show_state


def _patch_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
    import pyromind.config as cfg

    monkeypatch.setattr(
        cfg,
        "settings",
        Settings(
            db_path=str(tmp_path / "elib.sqlite"),
            projects_dir=str(tmp_path / "proj"),
            openrouter_api_key="dummy",
            audio_device="cpu",
        ),
    )


def _axis_vec(dim: int, index: int) -> list[float]:
    v = [0.0] * dim
    v[index] = 1.0
    return v


def _make_plan(*, avoid: list[str] | None = None) -> ShowPlan:
    avoid = avoid or []
    arc = [
        PlanSection(
            audio_section_index=i,
            intent=f"section {i} shell comet",
            intensity=0.5,
            density_per_min=12,
            dominant_colors=["gold"],
            preferred_effect_families=["shell", "comet"],
            avoid=avoid if i == 0 else [],
        )
        for i in range(3)
    ]
    return ShowPlan(
        title="T",
        concept="C",
        arc=arc,
        palette=Palette(
            primary=["#111"],
            secondary=["#222"],
            accent=["#333"],
            rationale="r",
        ),
        motifs=[],
        finale_concept="f",
        budget_distribution={"0": 0.34, "1": 0.33, "2": 0.33},
    )


def test_librarian_returns_candidates_for_all_sections(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    _patch_settings(monkeypatch, tmp_path)
    conn = get_connection()
    init_db(conn)
    seed_if_empty(conn)
    q = _axis_vec(1024, 0)
    for row in conn.execute("SELECT id FROM effects LIMIT 12"):
        vec_mod.insert_embedding(conn, str(row["id"]), q)
    conn.commit()
    conn.close()

    def _fake_embed(texts: list[str]) -> list[list[float]]:
        return [q for _ in texts]

    monkeypatch.setattr(el_mod, "embed_texts", _fake_embed)
    state = minimal_show_state()
    state["plan"] = _make_plan()
    out = el_mod.effect_librarian_node(state)
    cand = out["candidates"]
    assert cand is not None
    for i in range(3):
        assert i in cand.per_section
        assert len(cand.per_section[i]) >= 1


def test_librarian_respects_caliber_filter(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
    _patch_settings(monkeypatch, tmp_path)
    conn = get_connection()
    init_db(conn)
    seed_if_empty(conn)
    rows = [str(r["id"]) for r in conn.execute("SELECT id FROM effects LIMIT 20").fetchall()]
    half = len(rows) // 2
    for i, eid in enumerate(rows):
        conn.execute(
            "UPDATE effects SET caliber_in = ? WHERE id = ?",
            (3 if i < half else 8, eid),
        )
    q = _axis_vec(1024, 1)
    for eid in rows:
        vec_mod.insert_embedding(conn, eid, q)
    conn.commit()
    conn.close()

    monkeypatch.setattr(el_mod, "embed_texts", lambda texts: [q for _ in texts])
    state = minimal_show_state()
    uc = state["user_constraints"]
    if isinstance(uc, dict):
        uc = UserConstraints.model_validate(uc)
    state["user_constraints"] = uc.model_copy(update={"calibers_allowed": [3]})
    state["plan"] = _make_plan()
    out = el_mod.effect_librarian_node(state)
    cand = out["candidates"]
    for ranked in cand.per_section.values():
        for r in ranked:
            assert r.effect.caliber_in == 3


def test_librarian_respects_avoid_families(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
    _patch_settings(monkeypatch, tmp_path)
    conn = get_connection()
    init_db(conn)
    seed_if_empty(conn)
    mine_ids = [
        str(r["id"])
        for r in conn.execute(
            "SELECT id FROM effects WHERE lower(family) = 'mine' LIMIT 5"
        ).fetchall()
    ]
    assert mine_ids, "seed should include mine effects"
    q = _axis_vec(1024, 2)
    for row in conn.execute("SELECT id FROM effects LIMIT 15"):
        eid = str(row["id"])
        vec_mod.insert_embedding(conn, eid, q)
    conn.commit()
    conn.close()

    monkeypatch.setattr(el_mod, "embed_texts", lambda texts: [q for _ in texts])
    state = minimal_show_state()
    state["plan"] = _make_plan(avoid=["mine"])
    out = el_mod.effect_librarian_node(state)
    cand = out["candidates"]
    ranked0 = cand.per_section.get(0, [])
    for r in ranked0:
        assert r.effect.family.lower() != "mine"


def test_librarian_retrieval_precision(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
    _patch_settings(monkeypatch, tmp_path)
    conn = get_connection()
    init_db(conn)
    winner = "precision-winner"
    for i in range(10):
        eid = winner if i == 3 else f"precision-{i}"
        conn.execute(
            """
            INSERT INTO effects (
                id, name, family, caliber_in, colors, duration_s, height_m,
                burst_radius_m, prefire_ms, lift_time_ms, sound_level,
                recommended_use, description, vdl_params_json, source, license,
                provenance_url, redistributable
            ) VALUES (?, ?, 'shell', 3, ?, 4.0, 80.0, 20.0, 500, 500, 'medium', '',
            ?, NULL, 'test', 'CC0', NULL, 1)
            """,
            (eid, f"Name {i}", json.dumps(["red"]), f"unique token ZZTARGET{i}"),
        )
        vec_mod.insert_embedding(conn, eid, _axis_vec(1024, i))
    conn.commit()
    conn.close()

    query_vec = _axis_vec(1024, 3)

    def _fake_embed(texts: list[str]) -> list[list[float]]:
        return [query_vec for _ in texts]

    monkeypatch.setattr(el_mod, "embed_texts", _fake_embed)
    state = minimal_show_state()
    state["plan"] = _make_plan()
    out = el_mod.effect_librarian_node(state)
    cand = out["candidates"]
    top3 = [r.effect_id for r in cand.per_section[0][:3]]
    assert winner in top3
