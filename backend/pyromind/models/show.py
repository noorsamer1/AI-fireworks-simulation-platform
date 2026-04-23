"""Show and planning contracts shared across agents and REST API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, NotRequired, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from pyromind.models.audio import AudioAnalysis


class FiringSite(BaseModel):
    """Physical constraints for the firing location."""

    width_m: float = Field(gt=0)
    depth_m: float = Field(gt=0)
    max_ceiling_m: float = Field(gt=0)
    audience_distance_m: float = Field(gt=0)


class UserConstraints(BaseModel):
    """End-user constraints that guide generation (spec §7.0.1)."""

    duration_mode: Literal["full_song", "custom"] = "full_song"
    custom_duration_s: float | None = None
    mood_tags: list[str] = Field(default_factory=list)
    color_palette: list[str] | None = None
    budget_tier: Literal["demo", "small", "medium", "large", "mega"] = "medium"
    site: FiringSite
    calibers_allowed: list[int] = Field(default_factory=lambda: [2, 3, 4, 5, 6, 8])
    finale_style: Literal["crescendo", "cascade", "wall", "none"] = "crescendo"
    language: Literal["en", "ar"] = "en"
    random_seed: int = 42


class ShowBase(BaseModel):
    """Shared persisted-show fields."""

    song_path: str
    song_sha256: str
    constraints_json: dict[str, Any] = Field(default_factory=dict)
    state: str = "created"
    state_json: dict[str, Any] = Field(default_factory=dict)


class ShowCreate(ShowBase):
    """Create-show request (project scoped via path)."""

    project_id: str


class Show(ShowBase):
    """Persisted show row."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    created_at: datetime
    updated_at: datetime


class ShowSummary(BaseModel):
    """Lightweight show row for project detail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    song_path: str
    state: str
    created_at: datetime
    updated_at: datetime


class PlanSection(BaseModel):
    """High-level intent for a section."""

    audio_section_index: int
    intent: str
    intensity: float = Field(ge=0, le=1)
    density_per_min: int = Field(ge=0)
    dominant_colors: list[str] = Field(default_factory=list)
    preferred_effect_families: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class Motif(BaseModel):
    """Recurring visual idea represented in machine-readable form."""

    id: str
    description: str
    rule: dict[str, str | float | int | bool]


class ShowPlan(BaseModel):
    """Creative plan generated from audio plus constraints."""

    title: str
    concept: str
    arc: list[PlanSection] = Field(default_factory=list)
    palette: dict[str, list[str]] = Field(default_factory=dict)
    motifs: list[Motif] = Field(default_factory=list)
    finale_concept: str
    budget_distribution: dict[str, float] = Field(default_factory=dict)


class FiringScript(BaseModel):
    """Hardware-compatible cue sequence container."""

    cues: list[dict[str, Any]] = Field(default_factory=list)
    devices: list[dict[str, Any]] = Field(default_factory=list)
    total_shell_count: int = 0
    estimated_smoke_level: float = 0.0
    duration_s: float = 0.0


class SafetyReport(BaseModel):
    """Safety verdict and detailed violations."""

    passed: bool
    violations: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    stats: dict[str, float] = Field(default_factory=dict)


class SimulationArtifact(BaseModel):
    """Links to simulation outputs."""

    particle_plan_json_path: str
    mp4_preview_path: str | None = None
    duration_s: float
    peak_particle_count: int


class ShowState(TypedDict):
    """Shared LangGraph state (spec §7.0)."""

    project_id: str
    song_path: str
    user_constraints: UserConstraints
    language: Literal["en", "ar"]
    audio: NotRequired[AudioAnalysis]
    plan: NotRequired[ShowPlan]
    choreography: NotRequired[dict[str, Any]]
    firing_script: NotRequired[FiringScript]
    safety: NotRequired[SafetyReport]
    simulation: NotRequired[SimulationArtifact]
    critique: NotRequired[dict[str, Any]]
    exports: NotRequired[dict[str, str]]
    errors: list[str]
    revision_requests: list[str]
    seed: int
    trace_id: str
