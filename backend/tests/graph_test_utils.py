"""Shared LangGraph test helpers (fast audio stub, etc.)."""

from __future__ import annotations

import uuid

import pytest

from pyromind.agents import audio_analyst as aa_mod
from pyromind.agents import effect_librarian as el_mod
from pyromind.agents import show_director as sd_mod
from pyromind.agents.base import agent_node
from pyromind.graph.state import ShowState
from pyromind.models.audio import AudioAnalysis, Section
from pyromind.models.candidates import EffectCandidates
from pyromind.models.plan import Palette, PlanSection, ShowPlan
from pyromind.models.show import FiringSite, UserConstraints


def minimal_show_state(*, project_id: str = "test-123", song_path: str = "/tmp/fake.wav") -> ShowState:
    """Minimal valid ``ShowState`` for graph runs."""
    site = FiringSite(
        width_m=30.0,
        depth_m=20.0,
        max_ceiling_m=120.0,
        audience_distance_m=50.0,
    )
    uc = UserConstraints(site=site, language="en")
    return {
        "project_id": project_id,
        "song_path": song_path,
        "user_constraints": uc,
        "language": "en",
        "errors": [],
        "revision_requests": [],
        "seed": 42,
        "trace_id": str(uuid.uuid4()),
        "pending_events": [],
    }


def patch_fast_audio_analyst(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the audio analyst node with a cheap stub (no Demucs/embeddings)."""

    @agent_node("audio_analyst")
    def _fast_audio(state: ShowState) -> ShowState:
        analysis = AudioAnalysis(
            duration_s=1.0,
            sample_rate=44100,
            tempo_bpm=120.0,
            downbeats_s=[0.0, 0.5, 1.0],
            stems={
                "drums": "/stub/drums.wav",
                "bass": "/stub/bass.wav",
                "vocals": "/stub/vocals.wav",
                "other": "/stub/other.wav",
            },
            sections=[
                Section(
                    start_s=0.0,
                    end_s=1.0,
                    label="intro",
                    energy=0.5,
                    novelty=0.3,
                ),
            ],
            mert_embedding=[0.1, 0.2, 0.3, 0.4],
            clap_embeddings=[(0.25, [0.0, 1.0]), (0.75, [0.5, 0.5])],
        )
        return {**state, "audio": analysis}

    monkeypatch.setattr(aa_mod, "audio_analyst_node", _fast_audio)


def patch_stub_planning_agents(monkeypatch: pytest.MonkeyPatch) -> None:
    """Offline stubs for ShowDirector + EffectLibrarian (full graph tests)."""

    @agent_node("show_director")
    def _stub_sd(state: ShowState) -> ShowState:
        audio = state["audio"]
        if isinstance(audio, dict):
            audio = AudioAnalysis.model_validate(audio)
        n = max(len(audio.sections), 1)
        total = float(n)
        bd = {str(i): round(1.0 / total, 6) for i in range(n)}
        diff = 1.0 - sum(bd.values())
        if bd:
            last_key = str(n - 1)
            bd[last_key] = round(bd[last_key] + diff, 6)
        arc = [
            PlanSection(
                audio_section_index=i,
                intent="stub intent",
                intensity=0.5,
                density_per_min=12,
                dominant_colors=["gold"],
                preferred_effect_families=["shell"],
                avoid=[],
            )
            for i in range(n)
        ]
        plan = ShowPlan(
            title="Stub Plan",
            concept="Offline test stub.",
            arc=arc,
            palette=Palette(
                primary=["#d4af37"],
                secondary=["#222"],
                accent=["#fff"],
                rationale="stub",
            ),
            motifs=[],
            finale_concept="stub finale",
            budget_distribution=bd,
        )
        return {**state, "plan": plan}

    @agent_node("effect_librarian")
    def _stub_el(state: ShowState) -> ShowState:
        return {**state, "candidates": EffectCandidates()}

    monkeypatch.setattr(sd_mod, "show_director_node", _stub_sd)
    monkeypatch.setattr(el_mod, "effect_librarian_node", _stub_el)
