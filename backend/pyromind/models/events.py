"""WebSocket event payloads streamed to the frontend."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class WSEvent(BaseModel):
    """Base envelope for all sidecar WebSocket messages."""

    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentStarted(WSEvent):
    """Emitted when an agent run begins."""

    event_type: Literal["agent_started"] = "agent_started"
    agent_name: str
    trace_id: str


class AgentProgress(WSEvent):
    """Periodic progress update from a long-running agent."""

    event_type: Literal["agent_progress"] = "agent_progress"
    agent_name: str
    message: str
    progress: float = Field(ge=0.0, le=1.0)


class AgentCompleted(WSEvent):
    """Emitted when an agent finishes successfully."""

    event_type: Literal["agent_completed"] = "agent_completed"
    agent_name: str
    summary: str
    payload: dict[str, Any] | None = None


class AgentFailed(WSEvent):
    """Emitted when an agent errors."""

    event_type: Literal["agent_failed"] = "agent_failed"
    agent_name: str
    error: str


class ShowStateChanged(WSEvent):
    """Emitted when persisted show state advances."""

    event_type: Literal["show_state_changed"] = "show_state_changed"
    show_id: str
    new_state: str
    state_json: dict[str, Any] = Field(default_factory=dict)
