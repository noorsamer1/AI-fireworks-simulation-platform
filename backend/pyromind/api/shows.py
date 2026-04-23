"""Show generation endpoints."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import sqlite3
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from pyromind.api.deps import db_conn
from pyromind.catalog.db import get_connection
from pyromind.graph.state import ShowState
from pyromind.models.audio import AudioAnalysis
from pyromind.models.show import FiringSite, UserConstraints

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shows", tags=["shows"])

_TASKS: set[asyncio.Task[Any]] = set()

_NODE_TO_PHASE: dict[str, str] = {
    "audio_analyst": "analyzing",
    "show_director": "planning",
    "effect_librarian": "retrieving",
    "choreographer": "choreographing",
    "effect_caster": "casting",
    "safety_auditor": "auditing",
    "simulator": "simulating",
    "critic": "critiquing",
    "exporter": "exporting",
}


class ReviseRequest(BaseModel):
    """User revision message for the orchestrator."""

    message: str = Field(..., min_length=1)


def _json_default(value: object) -> object:
    """Serialize pydantic models into JSON-friendly structures."""
    if hasattr(value, "model_dump"):
        return value.model_dump()  # type: ignore[no-any-return]
    if hasattr(value, "__dict__"):
        return value.__dict__  # type: ignore[no-any-return]
    return str(value)


def _spawn(coro: asyncio.coroutines.Coroutine[Any, Any, None]) -> None:
    task = asyncio.create_task(coro)
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)


async def get_show_state_json(show_id: str) -> dict[str, Any] | None:
    """Load ``state_json`` for a show (async wrapper around SQLite)."""

    def _read() -> dict[str, Any] | None:
        conn = get_connection()
        try:
            row = conn.execute("SELECT state_json FROM shows WHERE id = ?", (show_id,)).fetchone()
            if row is None:
                return None
            return json.loads(row["state_json"] or "{}")
        finally:
            conn.close()

    return await asyncio.to_thread(_read)


async def _update_show_db(
    show_id: str,
    phase: str,
    state_values: dict[str, Any],
) -> None:
    """Persist ``state`` column and ``state_json``."""

    def _write() -> None:
        conn = get_connection()
        try:
            conn.execute(
                """
                UPDATE shows SET state = ?, state_json = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (phase, json.dumps(state_values, default=_json_default), show_id),
            )
            conn.commit()
        finally:
            conn.close()

    await asyncio.to_thread(_write)


async def _broadcast_pending_events(show_id: str, node_output: dict[str, Any]) -> None:
    from pyromind.api.ws import manager

    for pending in node_output.get("pending_events", []):
        await manager.broadcast(show_id, pending)


async def _forward_graph_stream(
    show_id: str,
    graph: Any,
    config: dict[str, Any],
    input_payload: Any,
) -> None:
    """Run ``graph.astream`` until interrupt or completion (no ``invoke``)."""
    async for event in graph.astream(input_payload, config=config):
        for node_name, node_output in event.items():
            if node_name.startswith("__"):
                continue
            if not isinstance(node_output, dict):
                continue
            await _broadcast_pending_events(show_id, node_output)
            snap = await graph.aget_state(config)
            values = snap.values if isinstance(snap.values, dict) else {}
            completed = list(values.get("agents_completed", []))
            if node_name not in completed:
                completed.append(node_name)
            merged = {**values, "agents_completed": completed}
            phase = _NODE_TO_PHASE.get(node_name, "running")
            await _update_show_db(show_id, phase, merged)


async def run_show_graph(show_id: str, initial_state: ShowState) -> None:
    """Run LangGraph with checkpoints; broadcast events; pause before exporter."""
    from pyromind.api.ws import manager
    from pyromind.graph.runtime import get_compiled_graph

    graph = get_compiled_graph()
    config: dict[str, Any] = {"configurable": {"thread_id": show_id}}
    try:
        await _forward_graph_stream(show_id, graph, config, initial_state)
        snap = await graph.aget_state(config)
        if snap.next == ("exporter",):
            await manager.broadcast(show_id, {"event_type": "awaiting_approval"})
            values = snap.values if isinstance(snap.values, dict) else {}
            merged = {**values, "awaiting_exporter": True}
            await _update_show_db(show_id, "awaiting_approval", merged)
        else:
            values = snap.values if isinstance(snap.values, dict) else {}
            merged = {**values, "awaiting_exporter": False}
            await _update_show_db(show_id, "done", merged)
    except Exception as exc:  # noqa: BLE001
        logger.error("[graph runner] show %s failed: %s", show_id, exc)
        await _update_show_db(show_id, "failed", {"error": str(exc)})
        from pyromind.api.ws import manager as mgr

        await mgr.broadcast(show_id, {"event_type": "show_failed", "error": str(exc)})


async def _approve_and_broadcast(show_id: str) -> None:
    from pyromind.api.ws import manager
    from pyromind.graph.runtime import get_compiled_graph

    graph = get_compiled_graph()
    config: dict[str, Any] = {"configurable": {"thread_id": show_id}}
    await manager.broadcast(show_id, {"event_type": "export_started"})
    await _forward_graph_stream(show_id, graph, config, None)
    snap = await graph.aget_state(config)
    values = snap.values if isinstance(snap.values, dict) else {}
    await _update_show_db(show_id, "done", {**values, "awaiting_exporter": False})


async def _revise_and_broadcast(show_id: str, message: str) -> None:
    from langgraph.types import Command

    from pyromind.api.ws import manager
    from pyromind.graph.runtime import get_compiled_graph

    graph = get_compiled_graph()
    config: dict[str, Any] = {"configurable": {"thread_id": show_id}}
    snap = await graph.aget_state(config)
    values = snap.values if isinstance(snap.values, dict) else {}
    revs = list(values.get("revision_requests", [])) + [message]
    cmd = Command(update={"revision_requests": revs}, goto="show_director")
    await _forward_graph_stream(show_id, graph, config, cmd)
    snap2 = await graph.aget_state(config)
    if snap2.next == ("exporter",):
        await manager.broadcast(show_id, {"event_type": "awaiting_approval"})
        vals = snap2.values if isinstance(snap2.values, dict) else {}
        await _update_show_db(show_id, "awaiting_approval", {**vals, "awaiting_exporter": True})
    else:
        vals = snap2.values if isinstance(snap2.values, dict) else {}
        await _update_show_db(show_id, "done", {**vals, "awaiting_exporter": False})


@router.post("/", status_code=status.HTTP_200_OK)
async def create_show(
    project_id: str = Form(...),
    song: UploadFile = File(...),
    language: str = Form("en"),
    conn: sqlite3.Connection = Depends(db_conn),
) -> dict[str, str]:
    """Accept a song upload and start show generation."""
    import pyromind.config as _pm_config

    allowed = {".wav", ".mp3", ".flac"}
    filename = song.filename or "song"
    ext = Path(filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type: {ext}",
        )

    row = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    body = await song.read()
    if not body:
        raise HTTPException(status_code=400, detail="Empty upload.")

    root = _pm_config.settings.projects_root()
    dest_dir = root / project_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"song{ext}"
    dest_path.write_bytes(body)

    song_sha = hashlib.sha256(body).hexdigest()
    show_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    site = FiringSite(
        width_m=30.0,
        depth_m=20.0,
        max_ceiling_m=120.0,
        audience_distance_m=50.0,
    )
    lang: Literal["en", "ar"] = "ar" if language.strip().lower() == "ar" else "en"
    uc = UserConstraints(site=site, language=lang)

    state: ShowState = {
        "project_id": project_id,
        "song_path": str(dest_path.resolve()),
        "user_constraints": uc,
        "language": lang,
        "errors": [],
        "revision_requests": [],
        "seed": _pm_config.settings.llm_seed,
        "trace_id": str(uuid.uuid4()),
        "pending_events": [],
    }

    conn.execute(
        """
        INSERT INTO shows (id, project_id, song_path, song_sha256, constraints_json, state, state_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            show_id,
            project_id,
            str(dest_path.resolve()),
            song_sha,
            json.dumps(uc.model_dump()),
            "analyzing",
            json.dumps({"created_at": now, "agents_completed": []}, default=_json_default),
        ),
    )
    conn.commit()

    _spawn(run_show_graph(show_id, state))
    return {"show_id": show_id, "status": "analyzing"}


@router.post("/{show_id}/approve")
async def approve_show(show_id: str) -> dict[str, str]:
    """Resume a graph paused before the exporter node."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT state FROM shows WHERE id = ?", (show_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Show not found.")
        if row["state"] != "awaiting_approval":
            raise HTTPException(
                status_code=400,
                detail="Show is not awaiting approval.",
            )
    finally:
        conn.close()

    _spawn(_approve_and_broadcast(show_id))
    return {"status": "exporting"}


@router.post("/{show_id}/revise")
async def revise_show(show_id: str, body: ReviseRequest) -> dict[str, str]:
    """Append a revision request and re-run from ``show_director``."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT id FROM shows WHERE id = ?", (show_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Show not found.")
    finally:
        conn.close()

    _spawn(_revise_and_broadcast(show_id, body.message))
    return {"status": "revising"}


@router.get("/{show_id}/status")
async def get_show_status(show_id: str, conn: sqlite3.Connection = Depends(db_conn)) -> dict[str, Any]:
    """Return show progress summary for the UI."""
    row = conn.execute(
        "SELECT id, state, state_json FROM shows WHERE id = ?",
        (show_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Show not found.")
    blob = json.loads(row["state_json"] or "{}")
    errors = blob.get("errors", []) if isinstance(blob.get("errors"), list) else []
    agents_completed = (
        blob.get("agents_completed", []) if isinstance(blob.get("agents_completed"), list) else []
    )
    return {
        "show_id": row["id"],
        "state": row["state"],
        "errors": errors,
        "agents_completed": agents_completed,
        "awaiting_approval": row["state"] == "awaiting_approval",
    }


@router.get("/{show_id}/audio")
def get_show_audio(show_id: str, conn: sqlite3.Connection = Depends(db_conn)) -> dict:
    """Return analyzed audio payload from ``state_json``."""
    row = conn.execute("SELECT state_json FROM shows WHERE id = ?", (show_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Show not found.")
    state_json = json.loads(row["state_json"] or "{}")
    audio_payload = state_json.get("audio")
    if not audio_payload:
        raise HTTPException(status_code=404, detail="Audio analysis not ready.")
    return AudioAnalysis.model_validate(audio_payload).model_dump()


@router.get("/{show_id}")
def get_show(show_id: str, conn: sqlite3.Connection = Depends(db_conn)) -> dict:
    """Return show row with current state blob."""
    row = conn.execute("SELECT * FROM shows WHERE id = ?", (show_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Show not found.")
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "song_path": row["song_path"],
        "state": row["state"],
        "state_json": json.loads(row["state_json"] or "{}"),
    }
