"""Effect retrieval output (EffectLibrarian) — spec §7.4."""

from __future__ import annotations

from pydantic import BaseModel, Field

from pyromind.models.effect import Effect


class RankedEffect(BaseModel):
    """One ranked catalog effect with score and UI tooltip text."""

    effect_id: str
    score: float = Field(ge=0.0)
    why: str
    effect: Effect


class EffectCandidates(BaseModel):
    """Grouped retrieval results for sections and motifs."""

    per_section: dict[int, list[RankedEffect]] = Field(default_factory=dict)
    per_motif: dict[str, list[RankedEffect]] = Field(default_factory=dict)
