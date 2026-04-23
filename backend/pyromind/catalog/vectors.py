"""sqlite-vec KNN operations for effect embeddings."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

import sqlite_vec

logger = logging.getLogger(__name__)


def serialize_vector(v: list[float]) -> bytes:
    """Serialize float list to sqlite-vec binary format."""
    return sqlite_vec.serialize_float32(v)


def insert_embedding(conn: sqlite3.Connection, effect_id: str, embedding: list[float]) -> None:
    """Insert or replace an embedding row for an effect."""
    conn.execute("DELETE FROM effects_vec WHERE effect_id = ?", (effect_id,))
    conn.execute(
        "INSERT INTO effects_vec(embedding, effect_id) VALUES (?, ?)",
        (serialize_vector(embedding), effect_id),
    )


def search_similar(
    conn: sqlite3.Connection,
    query_embedding: list[float],
    *,
    limit: int = 30,
    filters: dict[str, Any] | None = None,
    knn_pool: int | None = None,
) -> list[tuple[str, float]]:
    """Return ``(effect_id, distance)`` ordered by cosine distance ascending.

    Runs sqlite-vec KNN on ``effects_vec`` only (JOIN + WHERE on ``effects`` in
    the same statement is rejected by sqlite-vec), then applies catalog
    filters in Python while preserving KNN order.
    """
    filters = filters or {}
    pool = int(knn_pool if knn_pool is not None else max(limit * 25, 80))
    qbytes = serialize_vector(query_embedding)
    try:
        knn_rows = conn.execute(
            "SELECT effect_id, distance FROM effects_vec WHERE embedding MATCH ? AND k = ?",
            (qbytes, pool),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        logger.warning("vec search failed (%s); returning empty.", exc)
        return []
    if not knn_rows:
        return []

    ids = [str(r["effect_id"]) for r in knn_rows]
    placeholders = ",".join("?" * len(ids))
    eff_rows = conn.execute(
        f"SELECT * FROM effects WHERE id IN ({placeholders})",
        ids,
    ).fetchall()
    id_to_eff = {str(er["id"]): er for er in eff_rows}

    def _passes(row: sqlite3.Row) -> bool:
        if not bool(row["redistributable"] if row["redistributable"] is not None else 1):
            return False
        if filters.get("family") and str(row["family"]) != str(filters["family"]):
            return False
        if filters.get("caliber_in") is not None and row["caliber_in"] != filters["caliber_in"]:
            return False
        if filters.get("color"):
            needle = str(filters["color"])
            colors_cell = row["colors"] or ""
            if needle.lower() not in str(colors_cell).lower():
                return False
        return True

    out: list[tuple[str, float]] = []
    for r in knn_rows:
        eid = str(r["effect_id"])
        eff = id_to_eff.get(eid)
        if eff is None or not _passes(eff):
            continue
        out.append((eid, float(r["distance"])))
        if len(out) >= limit:
            break
    return out
