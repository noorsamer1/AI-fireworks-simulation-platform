"""SQLite checkpointer: pause before exporter, resume with approve."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest
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


@pytest.mark.asyncio
async def test_sqlite_checkpoint_pause_and_resume(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    stubs_mod.reset_exporter_invocations()
    patch_fast_audio_analyst(monkeypatch)
    patch_stub_planning_agents(monkeypatch)
    db_path = tmp_path / "cp.sqlite"
    conn = await aiosqlite.connect(str(db_path))
    saver = AsyncSqliteSaver(conn, serde=build_checkpoint_serde())
    await saver.setup()
    graph = compile_graph(saver, interrupt_before=["exporter"])
    cfg = {"configurable": {"thread_id": "sqlite-show"}}
    async for _ in graph.astream(minimal_show_state(project_id="test-123"), config=cfg):
        pass
    snap = await graph.aget_state(cfg)
    assert snap.next == ("exporter",)
    assert stubs_mod.EXPORTER_INVOCATIONS == 0
    await approve_and_export("sqlite-show", graph, str(db_path))
    assert stubs_mod.EXPORTER_INVOCATIONS == 1
    await conn.close()
