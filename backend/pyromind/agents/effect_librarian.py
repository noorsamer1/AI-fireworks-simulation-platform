"""
EffectLibrarianAgent — retrieves candidate effects per plan section and motif.

Embedding similarity plus rule-based scoring (no LLM).
"""

from __future__ import annotations

import logging
from typing import Any

from pyromind.agents.base import agent_node
from pyromind.catalog import repositories as repos
from pyromind.catalog.db import get_connection
from pyromind.catalog.embedder import embed_texts
from pyromind.catalog import vectors as vec_mod
from pyromind.graph.state import ShowState
from pyromind.models.candidates import EffectCandidates, RankedEffect
from pyromind.models.effect import Effect
from pyromind.models.plan import Motif, PlanSection, ShowPlan

logger = logging.getLogger(__name__)

TOP_K_PER_SECTION = 30
TOP_K_PER_MOTIF = 10


def _build_section_query(section: PlanSection) -> str:
    fams = " ".join(section.preferred_effect_families)
    return (
        f"{section.intent} {fams} intensity {section.intensity:.2f} "
        f"density_per_min {section.density_per_min} colors {' '.join(section.dominant_colors)}"
    )


def _apply_hard_filters(
    candidates: list[tuple[str, float]],
    conn: Any,
    calibers_allowed: list[int] | None,
    avoid_families: list[str],
) -> list[tuple[str, float]]:
    avoid = {a.strip().lower() for a in avoid_families}
    allowed = set(calibers_allowed) if calibers_allowed else None
    out: list[tuple[str, float]] = []
    for eid, dist in candidates:
        eff = repos.get_effect_by_id(conn, eid)
        if eff is None:
            continue
        if not eff.redistributable:
            continue
        if eff.family.lower() in avoid:
            continue
        if allowed is not None and eff.caliber_in is not None and eff.caliber_in not in allowed:
            continue
        out.append((eid, dist))
    return out


def _widen_calibers(calibers_allowed: list[int] | None) -> list[int] | None:
    if not calibers_allowed:
        return None
    out: set[int] = set()
    for c in calibers_allowed:
        for d in (c - 1, c, c + 1):
            if d > 0:
                out.add(d)
    return sorted(out)


def _score_and_rank(
    pairs: list[tuple[str, float]],
    preferred_families: list[str],
    conn: Any,
) -> list[RankedEffect]:
    pref = {f.lower() for f in preferred_families}
    ranked: list[RankedEffect] = []
    for eid, dist in pairs:
        eff = repos.get_effect_by_id(conn, eid)
        if eff is None:
            continue
        sem = max(0.0, min(1.0, 1.0 - float(dist)))
        rule = 1.0 if eff.family.lower() in pref else 0.0
        score = 0.7 * sem + 0.3 * rule
        why = f"cosine≈{1.0 - dist:.2f}; family_match={rule:.0f}"
        ranked.append(RankedEffect(effect_id=eid, score=score, why=why, effect=eff))
    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked


def _retrieve_for_query(
    conn: Any,
    query: str,
    limit: int,
    calibers_allowed: list[int] | None,
    avoid_families: list[str],
    preferred_families: list[str],
) -> list[RankedEffect]:
    qvec = embed_texts([query])[0]
    pairs = vec_mod.search_similar(conn, qvec, limit=limit * 4, knn_pool=max(120, limit * 8))
    filtered = _apply_hard_filters(pairs, conn, calibers_allowed, avoid_families)
    if len(filtered) < 5 and calibers_allowed:
        logger.warning("Few candidates (%s); widening caliber filter once", len(filtered))
        wide = _widen_calibers(calibers_allowed)
        filtered = _apply_hard_filters(
            vec_mod.search_similar(conn, qvec, limit=limit * 8, knn_pool=200),
            conn,
            wide,
            avoid_families,
        )
    return _score_and_rank(filtered[: limit * 2], preferred_families, conn)[:limit]


@agent_node("effect_librarian")
def effect_librarian_node(state: ShowState) -> ShowState:
    """Populate ``candidates`` from ``plan`` using sqlite-vec retrieval."""
    plan = state.get("plan")
    if plan is None:
        errs = list(state.get("errors", [])) + ["effect_librarian: missing plan"]
        return {**state, "errors": errs}
    if isinstance(plan, dict):
        plan = ShowPlan.model_validate(plan)
    if not isinstance(plan, ShowPlan):
        errs = list(state.get("errors", [])) + ["effect_librarian: invalid plan"]
        return {**state, "errors": errs}

    conn = get_connection()
    try:
        per_section: dict[int, list[RankedEffect]] = {}
        for sec in plan.arc:
            if not isinstance(sec, PlanSection):
                sec = PlanSection.model_validate(sec)
            q = _build_section_query(sec)
            uc = state["user_constraints"]
            ranked = _retrieve_for_query(
                conn,
                q,
                TOP_K_PER_SECTION,
                uc.calibers_allowed,
                sec.avoid,
                sec.preferred_effect_families,
            )
            per_section[sec.audio_section_index] = ranked

        per_motif: dict[str, list[RankedEffect]] = {}
        for m in plan.motifs:
            if not isinstance(m, Motif):
                m = Motif.model_validate(m)
            ranked = _retrieve_for_query(
                conn,
                m.description,
                TOP_K_PER_MOTIF,
                state["user_constraints"].calibers_allowed,
                [],
                [],
            )
            per_motif[m.id] = ranked

        candidates = EffectCandidates(per_section=per_section, per_motif=per_motif)
        for idx, ranked in candidates.per_section.items():
            logger.info("[EffectLibrarian] section %s: %s candidates", idx, len(ranked))
        for mid, ranked in candidates.per_motif.items():
            logger.info("[EffectLibrarian] motif %s: %s candidates", mid, len(ranked))
        total = sum(len(v) for v in candidates.per_section.values())
        logger.info(
            "[EffectLibrarian] summary: sections=%s total_ranked=%s motifs=%s",
            len(candidates.per_section),
            total,
            len(candidates.per_motif),
        )
        return {**state, "candidates": candidates}
    finally:
        conn.close()
