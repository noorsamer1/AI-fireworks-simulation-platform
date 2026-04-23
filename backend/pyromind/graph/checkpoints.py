"""Checkpoint management utilities for show resumption."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

    from pyromind.graph.state import ShowState


async def get_latest_checkpoint(show_id: str, db_path: str) -> dict[str, Any] | None:
    """Return metadata for the latest checkpoint tuple for ``thread_id=show_id``, or None."""
    import aiosqlite
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    from pyromind.graph.checkpoint_serde import build_checkpoint_serde

    async with aiosqlite.connect(db_path) as conn:
        saver = AsyncSqliteSaver(conn, serde=build_checkpoint_serde())
        await saver.setup()
        config = {"configurable": {"thread_id": show_id}}
        tup = await saver.aget_tuple(config)
        if tup is None:
            return None
        return {
            "checkpoint_id": tup.config.get("configurable", {}).get("checkpoint_id"),
            "checkpoint": tup.checkpoint,
        }


async def approve_and_export(
    show_id: str,
    compiled_graph: CompiledStateGraph[ShowState],
    db_path: str,
) -> None:
    """Resume a graph paused at ``interrupt_before=['exporter']``."""
    _ = db_path  # reserved for future per-show DB routing
    config = {"configurable": {"thread_id": show_id}}
    async for _ in compiled_graph.astream(None, config=config):
        pass


async def revise_from_show_director(
    show_id: str,
    revision_message: str,
    compiled_graph: CompiledStateGraph[ShowState],
    db_path: str,
) -> None:
    """Append a revision request and continue from ``show_director``."""
    _ = db_path
    from langgraph.types import Command

    config = {"configurable": {"thread_id": show_id}}
    snap = await compiled_graph.aget_state(config)
    values = snap.values
    if not isinstance(values, dict):
        values = {}
    revs = list(values.get("revision_requests", [])) + [revision_message]
    cmd = Command(update={"revision_requests": revs}, goto="show_director")
    async for _ in compiled_graph.astream(cmd, config=config):
        pass
