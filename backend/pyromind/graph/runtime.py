"""Long-lived LangGraph compiled graph + AsyncSqlite checkpointer (FastAPI lifespan)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiosqlite import Connection

    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    from langgraph.graph.state import CompiledStateGraph

    from pyromind.graph.state import ShowState

_compiled: CompiledStateGraph[ShowState] | None = None
_checkpointer: AsyncSqliteSaver | None = None
_conn: Connection | None = None


async def init_graph_runtime() -> None:
    """Open SQLite, create checkpointer, compile graph. Call once from app lifespan."""
    global _compiled, _checkpointer, _conn

    import aiosqlite
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    import pyromind.config as _pm_config
    from pyromind.graph.build import compile_graph
    from pyromind.graph.checkpoint_serde import build_checkpoint_serde

    db_path = str(_pm_config.settings.sqlite_path())
    _conn = await aiosqlite.connect(db_path)
    _checkpointer = AsyncSqliteSaver(_conn, serde=build_checkpoint_serde())
    await _checkpointer.setup()
    _compiled = compile_graph(_checkpointer, interrupt_before=["exporter"])


def get_compiled_graph() -> CompiledStateGraph[ShowState]:
    """Return the app-wide compiled graph (must call ``init_graph_runtime`` first)."""
    if _compiled is None:
        raise RuntimeError("Graph runtime not initialized; check FastAPI lifespan.")
    return _compiled


async def shutdown_graph_runtime() -> None:
    """Close the checkpointer connection."""
    global _compiled, _checkpointer, _conn

    _compiled = None
    _checkpointer = None
    if _conn is not None:
        await _conn.close()
        _conn = None
