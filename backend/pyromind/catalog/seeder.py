"""Populate the catalog with seed data when empty."""

from __future__ import annotations

import sqlite3
import uuid

from pyromind.catalog.db import rebuild_effects_fts
from pyromind.catalog.seed import SEED_EFFECTS


def seed_if_empty(conn: sqlite3.Connection) -> int:
    """Insert ``SEED_EFFECTS`` when the ``effects`` table has zero rows.

    Returns:
        Number of rows inserted (``0`` if the table was already populated).
    """
    total = conn.execute("SELECT COUNT(*) AS c FROM effects").fetchone()["c"]
    if total > 0:
        return 0
    inserted = 0
    for row in SEED_EFFECTS:
        effect_id = str(uuid.uuid4())
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
                row["name"],
                row["family"],
                row["caliber_in"],
                row["colors"],
                row["duration_s"],
                row["height_m"],
                row["burst_radius_m"],
                row["prefire_ms"],
                row["lift_time_ms"],
                row["sound_level"],
                row["recommended_use"],
                row["description"],
                row["vdl_params_json"],
                row["source"],
                row["license"],
                row["provenance_url"],
                row["redistributable"],
            ),
        )
        inserted += 1
    rebuild_effects_fts(conn)
    return inserted
