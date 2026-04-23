"""Base decorator for all PyroMind LangGraph agent nodes."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

from pyromind.graph.state import ShowState

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[[ShowState], ShowState])


def agent_node(agent_name: str) -> Callable[[F], F]:
    """Wrap a graph node: log, append ``pending_events`` deltas, catch exceptions."""

    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(state: ShowState) -> ShowState:
            logger.info("[%s] starting", agent_name)
            t0 = time.monotonic()
            try:
                result = fn(state)
                duration_ms = int((time.monotonic() - t0) * 1000)
                logger.info("[%s] completed in %dms", agent_name, duration_ms)
                out = {k: v for k, v in result.items() if k != "pending_events"}
                events: list[dict] = [
                    {"event_type": "agent_started", "agent_name": agent_name},
                    {
                        "event_type": "agent_completed",
                        "agent_name": agent_name,
                        "duration_ms": duration_ms,
                    },
                ]
                return {**out, "pending_events": events}
            except Exception as exc:  # noqa: BLE001
                duration_ms = int((time.monotonic() - t0) * 1000)
                logger.error("[%s] failed after %dms: %s", agent_name, duration_ms, exc)
                errs = list(state.get("errors", [])) + [f"{agent_name}: {exc}"]
                events = [
                    {"event_type": "agent_started", "agent_name": agent_name},
                    {
                        "event_type": "agent_failed",
                        "agent_name": agent_name,
                        "error": str(exc),
                        "duration_ms": duration_ms,
                    },
                ]
                return {**state, "errors": errs, "pending_events": events}

        return wrapper  # type: ignore[return-value]

    return decorator
