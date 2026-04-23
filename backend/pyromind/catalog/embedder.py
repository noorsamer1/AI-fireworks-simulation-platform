"""bge-m3 embeddings for catalog effects (Phase 4)."""

from __future__ import annotations

import logging
import sqlite3

import torch

import pyromind.config as _pm_config
from pyromind.catalog import vectors as vec_mod
from pyromind.catalog.db import row_to_effect_dict

logger = logging.getLogger(__name__)

BGE_MODEL = "BAAI/bge-m3"
_EMBED_DIM = 1024
_BATCH = 8


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate normalized bge-m3 embeddings (1024-dim) for texts.

    Loads the model on CPU or CUDA (when ``audio_device`` is cuda), encodes,
    then deletes the model to free RAM/VRAM.

    Args:
        texts: Non-empty list of strings to embed.

    Returns:
        One embedding vector per input string.
    """
    from sentence_transformers import SentenceTransformer

    if not texts:
        return []
    device = (
        "cuda"
        if _pm_config.settings.audio_device == "cuda" and torch.cuda.is_available()
        else "cpu"
    )
    model = SentenceTransformer(BGE_MODEL, device=device)
    try:
        with torch.no_grad():
            out = model.encode(
                texts,
                normalize_embeddings=True,
                batch_size=min(16, len(texts)),
                show_progress_bar=False,
            )
    finally:
        del model
        if device == "cuda":
            torch.cuda.empty_cache()
    return [out[i].tolist() for i in range(len(texts))]


def embed_effect(effect: dict[str, object]) -> list[float]:
    """Embed a catalog effect from its row/dict fields."""
    colors = effect.get("colors") or []
    colors_s = ", ".join(str(c) for c in colors) if isinstance(colors, list) else str(colors)
    name = str(effect.get("name", ""))
    family = str(effect.get("family", ""))
    desc = str(effect.get("description") or "")
    height = effect.get("height_m")
    dur = effect.get("duration_s")
    height_s = f"{height}m" if height is not None else "unknown height"
    dur_s = f"{dur}s" if dur is not None else "unknown duration"
    text = (
        f"{name}. {family} shell. Colors: {colors_s}. "
        f"Height: {height_s}. Duration: {dur_s}. {desc}"
    )
    return embed_texts([text])[0]


def build_embeddings_if_empty(conn: sqlite3.Connection) -> None:
    """Populate ``effects_vec`` when empty using bge-m3 over all ``effects`` rows."""
    row = conn.execute("SELECT COUNT(*) AS c FROM effects_vec").fetchone()
    if row is None or int(row["c"]) > 0:
        return
    rows = conn.execute("SELECT * FROM effects").fetchall()
    if not rows:
        return
    total = len(rows)
    logger.info("Building effect embeddings (%s rows)…", total)
    batch_ids: list[str] = []
    batch_texts: list[str] = []
    done = 0

    def _description_text(d: dict[str, object]) -> str:
        colors = d.get("colors") or []
        colors_s = ", ".join(str(c) for c in colors) if isinstance(colors, list) else str(colors)
        name = str(d.get("name", ""))
        family = str(d.get("family", ""))
        desc = str(d.get("description") or "")
        height = d.get("height_m")
        dur = d.get("duration_s")
        height_s = f"{height}m" if height is not None else "unknown height"
        dur_s = f"{dur}s" if dur is not None else "unknown duration"
        return (
            f"{name}. {family} shell. Colors: {colors_s}. "
            f"Height: {height_s}. Duration: {dur_s}. {desc}"
        )

    def flush() -> None:
        nonlocal done
        if not batch_ids:
            return
        embs = embed_texts(batch_texts)
        for eid, emb in zip(batch_ids, embs, strict=True):
            if len(emb) != _EMBED_DIM:
                msg = f"unexpected embedding dim {len(emb)}"
                raise RuntimeError(msg)
            vec_mod.insert_embedding(conn, eid, emb)
        done += len(batch_ids)
        if done % 10 == 0 or done == total:
            logger.info("Embedded %s / %s effects", done, total)
        batch_ids.clear()
        batch_texts.clear()

    for r in rows:
        d = row_to_effect_dict(r)
        batch_ids.append(str(d["id"]))
        batch_texts.append(_description_text(d))
        if len(batch_ids) >= _BATCH:
            flush()
    flush()
    logger.info("Effect embeddings complete (%s).", done)
