"""SQLite catalog: connections, schema bootstrap, and migrations."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import sqlite_vec

import pyromind.config as _pm_config

_MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS effects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    family TEXT NOT NULL,
    caliber_in INTEGER,
    colors TEXT NOT NULL,
    duration_s REAL,
    height_m REAL,
    burst_radius_m REAL,
    prefire_ms INTEGER,
    lift_time_ms INTEGER,
    sound_level TEXT,
    recommended_use TEXT,
    description TEXT,
    vdl_params_json TEXT,
    source TEXT NOT NULL,
    license TEXT NOT NULL,
    provenance_url TEXT,
    redistributable INTEGER NOT NULL DEFAULT 1,
    imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    importer_version TEXT NOT NULL DEFAULT '1.0.0'
);

CREATE TABLE IF NOT EXISTS effects_vec (
    effect_id TEXT PRIMARY KEY REFERENCES effects(id) ON DELETE CASCADE,
    embedding_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    site_config_json TEXT NOT NULL DEFAULT '{}',
    default_language TEXT NOT NULL DEFAULT 'en'
);

CREATE TABLE IF NOT EXISTS shows (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    song_path TEXT NOT NULL,
    song_sha256 TEXT NOT NULL,
    constraints_json TEXT NOT NULL DEFAULT '{}',
    state TEXT NOT NULL DEFAULT 'created',
    state_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_shows_project ON shows(project_id);
CREATE INDEX IF NOT EXISTS ix_shows_state ON shows(state);

CREATE VIRTUAL TABLE IF NOT EXISTS effects_fts USING fts5(
    name,
    description,
    content='effects',
    content_rowid='rowid',
    tokenize = 'porter unicode61'
);
"""


def get_connection() -> sqlite3.Connection:
    """Open a SQLite connection with WAL, foreign keys, and sqlite-vec."""
    path = _pm_config.settings.sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Apply ordered ``*.sql`` migrations from ``catalog/migrations``."""
    if not _MIGRATIONS_DIR.is_dir():
        return
    for path in sorted(_MIGRATIONS_DIR.glob("*.sql")):
        sql = path.read_text(encoding="utf-8").strip()
        if sql:
            conn.executescript(sql)


def init_db(conn: sqlite3.Connection | None = None) -> None:
    """Create catalog tables and indexes if they do not exist (idempotent).

    When ``conn`` is omitted, opens a dedicated connection, commits, and closes.
    When ``conn`` is provided, the caller owns the transaction boundary.
    """
    own = conn is None
    if own:
        conn = get_connection()
    try:
        conn.executescript(_INIT_SQL)
        migrate(conn)
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def rebuild_effects_fts(conn: sqlite3.Connection) -> None:
    """Rebuild the FTS5 index from the ``effects`` content table."""
    conn.execute("INSERT INTO effects_fts(effects_fts) VALUES('rebuild')")


def row_to_effect_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Map an ``effects`` row to kwargs for :class:`pyromind.models.effect.Effect`."""
    colors = json.loads(row["colors"]) if row["colors"] else []
    vdl = row["vdl_params_json"]
    vdl_dict = json.loads(vdl) if vdl else None
    return {
        "id": row["id"],
        "name": row["name"],
        "family": row["family"],
        "caliber_in": row["caliber_in"],
        "colors": colors,
        "duration_s": row["duration_s"],
        "height_m": row["height_m"],
        "burst_radius_m": row["burst_radius_m"],
        "prefire_ms": row["prefire_ms"],
        "lift_time_ms": row["lift_time_ms"],
        "sound_level": row["sound_level"],
        "recommended_use": row["recommended_use"],
        "description": row["description"],
        "vdl_params_json": vdl_dict,
        "source": row["source"],
        "license": row["license"],
        "provenance_url": row["provenance_url"],
        "redistributable": bool(row["redistributable"]),
        "imported_at": row["imported_at"],
        "importer_version": row["importer_version"],
    }
