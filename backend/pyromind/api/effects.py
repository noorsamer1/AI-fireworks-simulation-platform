"""Effects catalog REST routes."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pyromind.api.deps import db_conn
from pyromind.catalog import repositories as repos
from pyromind.models.effect import (
    Effect,
    EffectCreate,
    EffectsListResponse,
    SemanticSearchHit,
    SemanticSearchRequest,
)

router = APIRouter(prefix="/effects", tags=["effects"])


@router.get("", response_model=EffectsListResponse)
async def list_effects(
    conn: sqlite3.Connection = Depends(db_conn),
    q: str | None = Query(default=None, description="Substring match on name and description"),
    family: str | None = Query(default=None),
    caliber_in: int | None = Query(default=None),
    color: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> EffectsListResponse:
    """Return a paginated slice of the effects catalog with optional filters."""
    items, total = repos.list_effects_page(conn, q, family, caliber_in, color, limit, offset)
    conn.commit()
    return EffectsListResponse(items=items, total=total)


@router.get("/{effect_id}", response_model=Effect)
async def get_effect(
    effect_id: str,
    conn: sqlite3.Connection = Depends(db_conn),
) -> Effect:
    """Return a single effect by id."""
    effect = repos.get_effect_by_id(conn, effect_id)
    if effect is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Effect not found")
    return effect


@router.post("", response_model=Effect, status_code=status.HTTP_201_CREATED)
async def create_effect(
    body: EffectCreate,
    conn: sqlite3.Connection = Depends(db_conn),
) -> Effect:
    """Create a user-authored catalog entry."""
    payload = body.model_dump()
    effect = repos.insert_effect_from_create(conn, payload)
    conn.commit()
    return effect


@router.post("/search/semantic", response_model=list[SemanticSearchHit])
async def semantic_search_effects(
    body: SemanticSearchRequest,
    conn: sqlite3.Connection = Depends(db_conn),
) -> list[SemanticSearchHit]:
    """Rank effects for a natural-language query using FTS5 (BM25).

    TODO: replace with vec search in Phase 4.
    """
    rows = repos.search_effects_semantic_fts(conn, body.query, body.limit)
    conn.commit()
    return [SemanticSearchHit(effect=e, score=s, why=w) for e, s, w in rows]
