"""Graph builder for PyroMind show-generation pipeline."""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from pyromind.graph.state import ShowState


def build_graph_definition() -> StateGraph[ShowState]:
    """Construct the StateGraph without compiling (no I/O, no checkpointer)."""
    from pyromind.agents.audio_analyst import audio_analyst_node
    from pyromind.agents.effect_librarian import effect_librarian_node
    from pyromind.agents.show_director import show_director_node
    from pyromind.agents.stubs import (
        choreographer_stub,
        critic_stub,
        effect_caster_stub,
        exporter_stub,
        safety_auditor_stub,
        simulator_stub,
    )

    graph: StateGraph[ShowState] = StateGraph(ShowState)
    graph.add_node("audio_analyst", audio_analyst_node)
    graph.add_node("show_director", show_director_node)
    graph.add_node("effect_librarian", effect_librarian_node)
    graph.add_node("choreographer", choreographer_stub)
    graph.add_node("effect_caster", effect_caster_stub)
    graph.add_node("safety_auditor", safety_auditor_stub)
    graph.add_node("simulator", simulator_stub)
    graph.add_node("exporter", exporter_stub)
    graph.add_node("critic", critic_stub)

    graph.set_entry_point("audio_analyst")
    graph.add_edge("audio_analyst", "show_director")
    graph.add_edge("show_director", "effect_librarian")
    graph.add_edge("effect_librarian", "choreographer")
    graph.add_edge("choreographer", "effect_caster")
    graph.add_edge("effect_caster", "safety_auditor")
    graph.add_edge("safety_auditor", "simulator")
    graph.add_edge("simulator", "critic")
    graph.add_edge("critic", "exporter")
    graph.add_edge("exporter", END)
    return graph


def compile_graph(
    checkpointer: object,
    interrupt_before: list[str] | None = None,
) -> CompiledStateGraph[ShowState]:
    """Compile graph definition with the given checkpointer."""
    graph_def = build_graph_definition()
    return graph_def.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before or ["exporter"],
    )


def build_graph() -> CompiledStateGraph[ShowState]:
    """Compile without persistence (unit tests that do not need interrupts)."""
    return build_graph_definition().compile()
