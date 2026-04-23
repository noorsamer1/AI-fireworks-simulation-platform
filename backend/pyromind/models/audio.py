"""Audio analysis schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Section(BaseModel):
    """Detected musical section."""

    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    label: Literal[
        "intro",
        "verse",
        "chorus",
        "bridge",
        "drop",
        "breakdown",
        "outro",
        "instrumental",
    ]
    energy: float = Field(ge=0, le=1)
    novelty: float = Field(ge=0, le=1)


class AudioAnalysis(BaseModel):
    """Structured output from audio analysis agent."""

    duration_s: float
    sample_rate: int
    tempo_bpm: float
    tempo_curve: list[tuple[float, float]] = Field(default_factory=list)
    beats_s: list[float] = Field(default_factory=list)
    downbeats_s: list[float] = Field(default_factory=list)
    onsets_s: list[float] = Field(default_factory=list)
    key: str = "C"
    mode: Literal["major", "minor"] = "major"
    loudness_curve: list[float] = Field(default_factory=list)
    spectral_centroid_curve: list[float] = Field(default_factory=list)
    stems: dict[Literal["drums", "bass", "vocals", "other"], str] = Field(default_factory=dict)
    sections: list[Section] = Field(default_factory=list)
    mood_vector: list[float] = Field(default_factory=list)
    mert_embedding: list[float] = Field(default_factory=list)
    clap_embeddings: list[tuple[float, list[float]]] = Field(default_factory=list)
