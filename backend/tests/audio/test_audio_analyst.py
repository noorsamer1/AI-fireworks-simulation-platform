"""Integration-like tests for AudioAnalyst node."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

import pytest

import pyromind.config as _pm_config
from pyromind.agents.audio_analyst import audio_analyst_node
from pyromind.models.audio import AudioAnalysis


def _base_state(song_path: Path) -> dict:
    return {
        "project_id": "proj-1",
        "song_path": str(song_path),
        "user_constraints": {
            "duration_mode": "full_song",
            "custom_duration_s": None,
            "mood_tags": [],
            "color_palette": None,
            "budget_tier": "medium",
            "site": {
                "width_m": 10.0,
                "depth_m": 10.0,
                "max_ceiling_m": 80.0,
                "audience_distance_m": 60.0,
            },
            "calibers_allowed": [2, 3, 4],
            "finale_style": "crescendo",
            "language": "en",
            "random_seed": 42,
        },
        "language": "en",
        "errors": [],
        "revision_requests": [],
        "seed": 42,
        "trace_id": "trace-1",
    }


@pytest.mark.slow
def test_analysis_returns_valid_schema(sine_fixture: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_pm_config.settings, "audio_cache_dir", str(tmp_path))
    monkeypatch.setattr("torch.cuda.is_available", lambda: False)
    result = audio_analyst_node(_base_state(sine_fixture))
    assert "audio" in result
    AudioAnalysis.model_validate(result["audio"])


@pytest.mark.slow
def test_analysis_cache_hit(sine_fixture: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_pm_config.settings, "audio_cache_dir", str(tmp_path))
    monkeypatch.setattr("torch.cuda.is_available", lambda: False)
    state = _base_state(sine_fixture)
    start = perf_counter()
    audio_analyst_node(state)
    first = perf_counter() - start
    start = perf_counter()
    audio_analyst_node(state)
    second = perf_counter() - start
    assert second * 10 < first


def test_analysis_error_handling(tmp_path: Path) -> None:
    bad_state = _base_state(tmp_path / "missing.wav")
    result = audio_analyst_node(bad_state)
    assert result["errors"]


@pytest.mark.slow
def test_sections_minimum_two(sine_fixture: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_pm_config.settings, "audio_cache_dir", str(tmp_path))
    monkeypatch.setattr("torch.cuda.is_available", lambda: False)
    result = audio_analyst_node(_base_state(sine_fixture))
    assert len(result["audio"].sections) >= 2


@pytest.mark.slow
def test_beats_within_audio_duration(sine_fixture: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_pm_config.settings, "audio_cache_dir", str(tmp_path))
    monkeypatch.setattr("torch.cuda.is_available", lambda: False)
    result = audio_analyst_node(_base_state(sine_fixture))
    duration = result["audio"].duration_s
    assert all(0 <= beat <= duration for beat in result["audio"].beats_s)
