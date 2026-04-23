"""Data access helpers for catalog, projects, and shows."""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from typing import Any

from pyromind.catalog.db import rebuild_effects_fts, row_to_effect_dict
from pyromind.models.effect import Effect
from pyromind.models.project import Project, ProjectDetail
from pyromind.models.show import ShowSummary


def _parse_json_dict(raw: str | None) -> dict[str, Any]:
    """Parse a JSON object column, defaulting to empty dict."""
    if not raw:
        return {}
    return json.loads(raw)


def _project_from_row(row: sqlite3.Row) -> Project:
    """Build a :class:`Project` from a ``projects`` row."""
    return Project(
        id=row["id"],
        name=row["name"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        site_config_json=_parse_json_dict(row["site_config_json"]),
        default_language=row["default_language"],
    )


def _show_summary_from_row(row: sqlite3.Row) -> ShowSummary:
    """Build a :class:`ShowSummary` from a ``shows`` row."""
    return ShowSummary(
        id=row["id"],
        project_id=row["project_id"],
        song_path=row["song_path"],
        state=row["state"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_projects(conn: sqlite3.Connection) -> list[Project]:
    """Return all projects ordered by ``updated_at`` descending."""
    rows = conn.execute(
        "SELECT * FROM projects ORDER BY datetime(updated_at) DESC",
    ).fetchall()
    return [_project_from_row(r) for r in rows]


def create_project(conn: sqlite3.Connection, name: str) -> Project:
    """Insert a project and return the hydrated model."""
    pid = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO projects (id, name, site_config_json, default_language)
        VALUES (?, ?, '{}', 'en')
        """,
        (pid, name),
    )
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
    assert row is not None
    return _project_from_row(row)


def get_project_detail(conn: sqlite3.Connection, project_id: str) -> ProjectDetail | None:
    """Return a project with nested show summaries, or ``None`` if missing."""
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        return None
    shows = conn.execute(
        """
        SELECT id, project_id, song_path, state, created_at, updated_at
        FROM shows WHERE project_id = ? ORDER BY datetime(updated_at) DESC
        """,
        (project_id,),
    ).fetchall()
    base = _project_from_row(row)
    return ProjectDetail(
        **base.model_dump(),
        shows=[_show_summary_from_row(s) for s in shows],
    )


def delete_project(conn: sqlite3.Connection, project_id: str) -> bool:
    """Delete a project (cascades shows). Returns whether a row was removed."""
    cur = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    return cur.rowcount > 0


def count_effects_filtered(
    conn: sqlite3.Connection,
    q: str | None,
    family: str | None,
    caliber_in: int | None,
    color: str | None,
) -> int:
    """Count effects matching optional filters."""
    sql = "SELECT COUNT(*) AS c FROM effects WHERE 1=1"
    params: list[Any] = []
    sql, params = _append_effect_filters(sql, params, q, family, caliber_in, color)
    row = conn.execute(sql, params).fetchone()
    return int(row["c"])


def _append_effect_filters(
    sql: str,
    params: list[Any],
    q: str | None,
    family: str | None,
    caliber_in: int | None,
    color: str | None,
) -> tuple[str, list[Any]]:
    """Append WHERE fragments for catalog filters."""
    if q:
        sql += " AND (name LIKE ? COLLATE NOCASE OR IFNULL(description,'') LIKE ? COLLATE NOCASE)"
        like = f"%{q}%"
        params.extend([like, like])
    if family:
        sql += " AND family = ?"
        params.append(family)
    if caliber_in is not None:
        sql += " AND caliber_in = ?"
        params.append(caliber_in)
    if color:
        sql += (
            " AND EXISTS (SELECT 1 FROM json_each(effects.colors) AS j "
            "WHERE lower(j.value) = lower(?))"
        )
        params.append(color)
    return sql, params


def list_effects_page(
    conn: sqlite3.Connection,
    q: str | None,
    family: str | None,
    caliber_in: int | None,
    color: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Effect], int]:
    """Return a page of effects plus total count."""
    total = count_effects_filtered(conn, q, family, caliber_in, color)
    sql = "SELECT * FROM effects WHERE 1=1"
    params: list[Any] = []
    sql, params = _append_effect_filters(sql, params, q, family, caliber_in, color)
    sql += " ORDER BY family, name LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = conn.execute(sql, params).fetchall()
    return [Effect.model_validate(row_to_effect_dict(r)) for r in rows], total


def get_effect_by_id(conn: sqlite3.Connection, effect_id: str) -> Effect | None:
    """Return a single effect by primary key."""
    row = conn.execute("SELECT * FROM effects WHERE id = ?", (effect_id,)).fetchone()
    if row is None:
        return None
    return Effect.model_validate(row_to_effect_dict(row))


def insert_effect_from_create(conn: sqlite3.Connection, data: dict[str, Any]) -> Effect:
    """Persist a user-authored effect from a validated payload dict."""
    effect_id = str(uuid.uuid4())
    colors_json = json.dumps(data.get("colors") or [])
    vdl = data.get("vdl_params_json")
    vdl_json = json.dumps(vdl) if vdl is not None else None
    conn.execute(
        """
        INSERT INTO effects (
            id, name, family, caliber_in, colors, duration_s, height_m,
            burst_radius_m, prefire_ms, lift_time_ms, sound_level,
            recommended_use, description, vdl_params_json, source, license,
            provenance_url, redistributable
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            effect_id,
            data["name"],
            data["family"],
            data.get("caliber_in"),
            colors_json,
            data.get("duration_s"),
            data.get("height_m"),
            data.get("burst_radius_m"),
            data.get("prefire_ms"),
            data.get("lift_time_ms"),
            data.get("sound_level"),
            data.get("recommended_use"),
            data.get("description"),
            vdl_json,
            data.get("source", "generative"),
            data.get("license", "pyromind-internal"),
            data.get("provenance_url"),
            int(bool(data.get("redistributable", True))),
        ),
    )
    row = conn.execute("SELECT * FROM effects WHERE id = ?", (effect_id,)).fetchone()
    assert row is not None
    rebuild_effects_fts(conn)
    return Effect.model_validate(row_to_effect_dict(row))


def search_effects_semantic_fts(
    conn: sqlite3.Connection,
    query: str,
    limit: int,
) -> list[tuple[Effect, float, str]]:
    """Rank effects using SQLite FTS5 BM25 (placeholder for sqlite-vec in Phase 4)."""
    # TODO: replace with vec search in Phase 4
    tokens = [re.sub(r"[^\w]+", "", t) for t in query.split() if t.strip()]
    fts_parts = [f"{t}*" for t in tokens if t]
    if not fts_parts:
        return []
    fts_query = " AND ".join(fts_parts)
    sql = """
    SELECT e.*, bm25(effects_fts) AS rank
    FROM effects_fts
    JOIN effects AS e ON e.rowid = effects_fts.rowid
    WHERE effects_fts MATCH ?
    ORDER BY rank ASC
    LIMIT ?
    """
    rows = conn.execute(sql, (fts_query, limit)).fetchall()
    results: list[tuple[Effect, float, str]] = []
    for row in rows:
        rank = float(row["rank"])
        score = float(-rank)
        why = f"fts5:bm25 rank on query `{fts_query}`"
        effect = Effect.model_validate(row_to_effect_dict(row))
        results.append((effect, score, why))
    return results


def update_effect_redistributable(conn: sqlite3.Connection, effect_id: str, flag: bool) -> None:
    """Update redistributable flag (tests / admin)."""
    conn.execute(
        "UPDATE effects SET redistributable = ? WHERE id = ?",
        (int(flag), effect_id),
    )
