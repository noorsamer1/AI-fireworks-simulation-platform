"""Show plan contracts (ShowDirector output) — spec §7.3."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_VALID_FAMILIES = frozenset(
    {"shell", "comet", "mine", "cake", "candle", "ground"},
)


class Palette(BaseModel):
    """Color direction for the show."""

    primary: list[str] = Field(default_factory=list)
    secondary: list[str] = Field(default_factory=list)
    accent: list[str] = Field(default_factory=list)
    rationale: str = ""


class Motif(BaseModel):
    """Recurring visual idea with a machine-readable rule payload."""

    id: str
    description: str
    rule: dict[str, Any] = Field(default_factory=dict)


class PlanSection(BaseModel):
    """High-level intent for one audio section (1:1 with audio sections)."""

    audio_section_index: int = Field(ge=0)
    intent: str
    intensity: float = Field(ge=0.0, le=1.0)
    density_per_min: int = Field(ge=1, le=60)
    dominant_colors: list[str] = Field(default_factory=list)
    preferred_effect_families: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)

    @field_validator("preferred_effect_families")
    @classmethod
    def _families(cls, v: list[str]) -> list[str]:
        """Normalize unknown families to closest allowed token or drop (spec: warn, not error)."""
        out: list[str] = []
        for f in v:
            key = f.strip().lower().replace(" ", "_").replace("-", "_")
            if key in _VALID_FAMILIES:
                out.append(key)
        return out


class ShowPlan(BaseModel):
    """Creative plan from audio + client brief."""

    model_config = ConfigDict(from_attributes=True)

    title: str
    concept: str
    arc: list[PlanSection] = Field(default_factory=list)
    palette: Palette
    motifs: list[Motif] = Field(default_factory=list)
    finale_concept: str
    budget_distribution: dict[str, float] = Field(default_factory=dict)

    @field_validator("budget_distribution")
    @classmethod
    def _budget_non_negative(cls, v: dict[str, float]) -> dict[str, float]:
        for key, val in v.items():
            if val < 0:
                msg = f"budget_distribution[{key!r}] must be >= 0"
                raise ValueError(msg)
        return v
