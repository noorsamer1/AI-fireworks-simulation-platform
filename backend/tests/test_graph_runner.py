"""LangGraph interrupt, resume, and pending_events coverage."""

from __future__ import annotations

from pathlib import Path

import pytest
import aiosqlite
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from pyromind.agents import stubs as stubs_mod
from pyromind.graph.build import compile_graph
from pyromind.graph.checkpoint_serde import build_checkpoint_serde
from pyromind.graph.checkpoints import approve_and_export

from tests.graph_test_utils import (
    minimal_show_state,
    patch_fast_audio_analyst,
    patch_stub_planning_agents,
)

_AGENT_ORDER = (
    "audio_analyst",
    "show_director",
    "effect_librarian",
    "choreographer",
    "effect_caster",
    "safety_auditor",
    "simulator",
    "critic",
)


@pytest.fixture(autouse=True)
def _reset_exporter() -> None:
    stubs_mod.reset_exporter_invocations()
    yield
    stubs_mod.reset_exporter_invocations()


def _interrupt_graph(monkeypatch: pytest.MonkeyPatch):
    patch_fast_audio_analyst(monkeypatch)
    patch_stub_planning_agents(monkeypatch)
    return compile_graph(
        MemorySaver(serde=build_checkpoint_serde()),
        interrupt_before=["exporter"],
    )


@pytest.mark.asyncio
async def test_graph_pauses_before_exporter(monkeypatch: pytest.MonkeyPatch) -> None:
    graph = _interrupt_graph(monkeypatch)
    cfg = {"configurable": {"thread_id": "show-pause"}}
    async for _ in graph.astream(minimal_show_state(), config=cfg):
        pass
    snap = await graph.aget_state(cfg)
    assert snap.next == ("exporter",)
    assert stubs_mod.EXPORTER_INVOCATIONS == 0


@pytest.mark.asyncio
async def test_graph_resumes_after_approve(monkeypatch: pytest.MonkeyPatch) -> None:
    graph = _interrupt_graph(monkeypatch)
    cfg = {"configurable": {"thread_id": "show-resume"}}
    async for _ in graph.astream(minimal_show_state(), config=cfg):
        pass
    assert stubs_mod.EXPORTER_INVOCATIONS == 0
    await approve_and_export("show-resume", graph, "unused")
    assert stubs_mod.EXPORTER_INVOCATIONS == 1


@pytest.mark.asyncio
async def test_graph_records_pending_events(monkeypatch: pytest.MonkeyPatch) -> None:
    collected: list[dict] = []
    graph = _interrupt_graph(monkeypatch)
    cfg = {"configurable": {"thread_id": "show-events"}}
    async for event in graph.astream(minimal_show_state(), config=cfg):
        for _node, out in event.items():
            if _node.startswith("__") or not isinstance(out, dict):
                continue
            collected.extend(out.get("pending_events", []))

    started = {e["agent_name"] for e in collected if e.get("event_type") == "agent_started"}
    completed = {e["agent_name"] for e in collected if e.get("event_type") == "agent_completed"}
    assert started == completed == set(_AGENT_ORDER)
    assert "exporter" not in started


@pytest.mark.asyncio
async def test_checkpoint_roundtrip_preserves_audio_analysis(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """AudioAnalysis survives SQLite checkpoint write + read on a new connection."""
    from pyromind.models.audio import AudioAnalysis

    patch_fast_audio_analyst(monkeypatch)
    patch_stub_planning_agents(monkeypatch)
    db_path = tmp_path / "roundtrip.sqlite"
    serde = build_checkpoint_serde()
    thread_id = "roundtrip-audio"

    conn1 = await aiosqlite.connect(str(db_path))
    saver1 = AsyncSqliteSaver(conn1, serde=serde)
    await saver1.setup()
    graph1 = compile_graph(saver1, interrupt_before=["show_director"])
    cfg = {"configurable": {"thread_id": thread_id}}
    async for _ in graph1.astream(minimal_show_state(), config=cfg):
        pass
    await conn1.close()

    conn2 = await aiosqlite.connect(str(db_path))
    saver2 = AsyncSqliteSaver(conn2, serde=serde)
    await saver2.setup()
    graph2 = compile_graph(saver2, interrupt_before=["show_director"])
    snap = await graph2.aget_state(cfg)
    await conn2.close()

    raw = snap.values.get("audio")
    assert raw is not None
    audio = raw if isinstance(raw, AudioAnalysis) else AudioAnalysis.model_validate(raw)

    assert len(audio.sections) >= 1
    assert len(audio.mert_embedding) >= 1
    assert len(audio.clap_embeddings) >= 1
    assert all(len(vec) >= 1 for _t, vec in audio.clap_embeddings)
