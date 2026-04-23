"""Shared LangGraph state contract."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, NotRequired, TypedDict

from pyromind.models.audio import AudioAnalysis
from pyromind.models.candidates import EffectCandidates
from pyromind.models.plan import ShowPlan
from pyromind.models.show import FiringScript, SafetyReport, SimulationArtifact, UserConstraints


class ShowState(TypedDict):
    """State object shared across all PyroMind graph nodes."""

    project_id: str
    song_path: str
    user_constraints: UserConstraints
    language: Literal["en", "ar"]
    audio: NotRequired[AudioAnalysis]
    plan: NotRequired[ShowPlan]
    candidates: NotRequired[EffectCandidates]
    choreography: NotRequired[dict]
    firing_script: NotRequired[FiringScript]
    safety: NotRequired[SafetyReport]
    simulation: NotRequired[SimulationArtifact]
    critique: NotRequired[dict]
    exports: NotRequired[dict[str, str]]
    errors: list[str]
    revision_requests: list[str]
    seed: int
    trace_id: str
    pending_events: Annotated[list[dict[str, Any]], operator.add]
