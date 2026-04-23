"""Stub graph nodes for not-yet-implemented agents."""

from __future__ import annotations

from pyromind.agents.base import agent_node
from pyromind.graph.state import ShowState

# Test hooks: incremented each time the exporter stub body runs.
EXPORTER_INVOCATIONS: int = 0


def reset_exporter_invocations() -> None:
    """Reset exporter call counter (used by tests)."""
    global EXPORTER_INVOCATIONS
    EXPORTER_INVOCATIONS = 0


@agent_node("show_director")
def show_director_stub(state: ShowState) -> ShowState:
    """Stub ShowDirector."""
    return state


@agent_node("effect_librarian")
def effect_librarian_stub(state: ShowState) -> ShowState:
    return state


@agent_node("choreographer")
def choreographer_stub(state: ShowState) -> ShowState:
    return state


@agent_node("effect_caster")
def effect_caster_stub(state: ShowState) -> ShowState:
    return state


@agent_node("safety_auditor")
def safety_auditor_stub(state: ShowState) -> ShowState:
    return state


@agent_node("simulator")
def simulator_stub(state: ShowState) -> ShowState:
    return state


@agent_node("exporter")
def exporter_stub(state: ShowState) -> ShowState:
    global EXPORTER_INVOCATIONS
    EXPORTER_INVOCATIONS += 1
    return {**state, "exports": {"vdl": "stub://placeholder"}}


@agent_node("critic")
def critic_stub(state: ShowState) -> ShowState:
    return state
