"""Effect catalog Pydantic models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EffectBase(BaseModel):
    """Shared effect attributes."""

    name: str
    family: str
    caliber_in: int | None = None
    colors: list[str] = Field(default_factory=list)
    duration_s: float | None = None
    height_m: float | None = None
    burst_radius_m: float | None = None
    prefire_ms: int | None = None
    lift_time_ms: int | None = None
    sound_level: str | None = None
    recommended_use: str | None = None
    description: str | None = None
    vdl_params_json: dict[str, Any] | None = None


class EffectCreate(EffectBase):
    """Payload for creating a user-authored effect."""

    source: str = "generative"
    license: str = "pyromind-internal"
    provenance_url: str | None = None
    redistributable: bool = True


class Effect(EffectBase):
    """Full effect row returned from the catalog."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    license: str
    provenance_url: str | None
    redistributable: bool
    imported_at: datetime
    importer_version: str


class EffectsListResponse(BaseModel):
    """Paginated effects listing."""

    items: list[Effect]
    total: int


class SemanticSearchRequest(BaseModel):
    """Body for placeholder semantic search (FTS5 today; vec in Phase 4)."""

    query: str
    limit: int = 5


class SemanticSearchHit(BaseModel):
    """One ranked effect from semantic search."""

    effect: Effect
    score: float
    why: str
