"""ShowDirector agent unit tests (mocked LLM)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from pyromind.agents import show_director as sd_mod
from pyromind.models.audio import AudioAnalysis, Section
from pyromind.models.plan import Palette, PlanSection, ShowPlan
from tests.graph_test_utils import minimal_show_state


def _three_section_audio() -> AudioAnalysis:
    labels: list = ["intro", "verse", "chorus"]
    sections = [
        Section(
            start_s=float(i),
            end_s=float(i) + 1.0,
            label=labels[i],
            energy=0.3 + 0.1 * i,
            novelty=0.2,
        )
        for i in range(3)
    ]
    return AudioAnalysis(
        duration_s=12.0,
        sample_rate=44100,
        tempo_bpm=120.0,
        sections=sections,
        mood_vector=[0.1, 0.2, 0.3],
    )


def _valid_plan_dict() -> dict[str, Any]:
    arc = [
        PlanSection(
            audio_section_index=i,
            intent=f"intent {i}",
            intensity=0.5,
            density_per_min=10 + i,
            dominant_colors=["gold"],
            preferred_effect_families=["shell"],
            avoid=[],
        )
        for i in range(3)
    ]
    plan = ShowPlan(
        title="T",
        concept="C",
        arc=arc,
        palette=Palette(primary=["#000"], secondary=["#111"], accent=["#222"], rationale="r"),
        motifs=[],
        finale_concept="f",
        budget_distribution={"0": 0.33, "1": 0.33, "2": 0.34},
    )
    return json.loads(plan.model_dump_json())


def _as_show_plan(plan: object) -> ShowPlan:
    return plan if isinstance(plan, ShowPlan) else ShowPlan.model_validate(plan)


def test_show_director_returns_valid_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Resp:
        def __init__(self, content: str) -> None:
            self.content = content

    class _LLM:
        def invoke(self, _messages: object) -> _Resp:
            return _Resp(json.dumps(_valid_plan_dict()))

    monkeypatch.setattr(sd_mod, "get_llm", lambda **_: _LLM())
    state = minimal_show_state()
    state["audio"] = _three_section_audio()
    out = sd_mod.show_director_node(state)
    raw_plan = out.get("plan")
    assert raw_plan is not None
    sp = _as_show_plan(raw_plan)
    assert len(sp.arc) == 3
    assert sum(sp.budget_distribution.values()) == pytest.approx(1.0)
    for sec in sp.arc:
        assert sec.intent
        assert sec.preferred_effect_families


def test_show_director_normalizes_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    d = _valid_plan_dict()
    d["budget_distribution"] = {"0": 0.49, "1": 0.49, "2": 0.0}

    class _Resp:
        content = json.dumps(d)

    class _LLM:
        def invoke(self, _m: object) -> _Resp:
            return _Resp()

    monkeypatch.setattr(sd_mod, "get_llm", lambda **_: _LLM())
    state = minimal_show_state()
    state["audio"] = _three_section_audio()
    out = sd_mod.show_director_node(state)
    plan = _as_show_plan(out["plan"])
    assert sum(plan.budget_distribution.values()) == pytest.approx(1.0)


def test_show_director_retries_on_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    class _Resp:
        def __init__(self, content: str) -> None:
            self.content = content

    class _LLM:
        def invoke(self, _m: object) -> _Resp:
            calls.append(1)
            if len(calls) == 1:
                return _Resp("NOT JSON {{{")
            return _Resp(json.dumps(_valid_plan_dict()))

    monkeypatch.setattr(sd_mod, "get_llm", lambda **_: _LLM())
    state = minimal_show_state()
    state["audio"] = _three_section_audio()
    out = sd_mod.show_director_node(state)
    assert out.get("plan") is not None
    assert len(calls) >= 2


def test_show_director_error_on_all_retries_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Resp:
        content = "not json at all"

    class _LLM:
        def invoke(self, _m: object) -> _Resp:
            return _Resp()

    monkeypatch.setattr(sd_mod, "get_llm", lambda **_: _LLM())
    state = minimal_show_state()
    state["audio"] = _three_section_audio()
    out = sd_mod.show_director_node(state)
    assert out.get("plan") is None
    assert any("show_director" in e for e in out.get("errors", []))


def test_build_user_message_includes_constraints() -> None:
    state = minimal_show_state()
    state["audio"] = _three_section_audio()
    msg = sd_mod._build_user_message(state)
    data = json.loads(msg)
    assert data["song"]["sections_count"] == 3
    assert data["constraints"]["budget_tier"] == "medium"
    assert "site" in data["constraints"]


def test_normalize_budget_scales() -> None:
    d = {"budget_distribution": {"a": 0.49, "b": 0.49}}
    out = sd_mod._normalize_budget(dict(d))
    s = sum(out["budget_distribution"].values())
    assert s == pytest.approx(1.0)
