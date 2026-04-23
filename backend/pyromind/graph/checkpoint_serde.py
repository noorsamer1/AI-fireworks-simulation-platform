"""LangGraph checkpoint serde with allowlisted project models for msgpack round-trips."""

from __future__ import annotations

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer


def build_checkpoint_serde() -> JsonPlusSerializer:
    """Serializer used with AsyncSqliteSaver / MemorySaver for lossless Pydantic state.

    Register every ``BaseModel`` type that may appear in ``ShowState`` so strict
    msgpack deserialization does not block or corrupt nested structures.
    """
    return JsonPlusSerializer(
        allowed_msgpack_modules=[
            ("pyromind.models.audio", "Section"),
            ("pyromind.models.audio", "AudioAnalysis"),
            ("pyromind.models.candidates", "RankedEffect"),
            ("pyromind.models.candidates", "EffectCandidates"),
            ("pyromind.models.effect", "Effect"),
            ("pyromind.models.plan", "Palette"),
            ("pyromind.models.plan", "Motif"),
            ("pyromind.models.plan", "PlanSection"),
            ("pyromind.models.plan", "ShowPlan"),
            ("pyromind.models.show", "FiringSite"),
            ("pyromind.models.show", "UserConstraints"),
            ("pyromind.models.show", "FiringScript"),
            ("pyromind.models.show", "SafetyReport"),
            ("pyromind.models.show", "SimulationArtifact"),
        ],
    )
