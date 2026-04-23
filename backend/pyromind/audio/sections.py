"""Structural segmentation for musical sections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import librosa
import numpy as np
from scipy.signal import find_peaks

SectionLabel = Literal[
    "intro",
    "verse",
    "chorus",
    "bridge",
    "drop",
    "breakdown",
    "outro",
    "instrumental",
]


@dataclass
class Section:
    start_s: float
    end_s: float
    label: SectionLabel
    energy: float
    novelty: float


def segment_audio(
    audio: np.ndarray,
    sr: int,
    mert_embeddings: list[tuple[float, list[float]]] | None = None,
) -> list[Section]:
    """Segment audio into coarse structural sections."""
    duration = float(len(audio) / sr)
    boundaries = [0.0, duration]
    if mert_embeddings:
        emb = np.array([row[1] for row in mert_embeddings], dtype=np.float32)
        if len(emb) > 2:
            novelty = np.linalg.norm(np.diff(emb, axis=0), axis=1)
            peaks, _ = find_peaks(novelty, distance=2)
            times = [float(mert_embeddings[i][0]) for i in peaks]
            boundaries = [0.0] + sorted([t for t in times if 10 < t < duration - 10]) + [duration]
    else:
        chroma = librosa.feature.chroma_cqt(y=audio, sr=sr)
        _, beats = librosa.beat.beat_track(y=audio, sr=sr)
        if len(beats) > 8:
            times = librosa.frames_to_time(beats[::16], sr=sr)
            boundaries = [0.0] + [float(t) for t in times if 10 < t < duration - 10] + [duration]

    boundaries = sorted(set(boundaries))
    chunks: list[Section] = []
    for idx in range(len(boundaries) - 1):
        start = boundaries[idx]
        end = boundaries[idx + 1]
        if end - start < 10:
            continue
        seg = audio[int(start * sr) : int(end * sr)]
        energy = float(np.sqrt(np.mean(np.square(seg))) if len(seg) else 0.0)
        chunks.append(Section(start, end, "verse", min(1.0, energy * 3), 0.0))

    if len(chunks) < 2:
        mid = max(duration / 2, 10.0)
        chunks = [
            Section(0.0, mid, "intro", 0.3, 0.0),
            Section(mid, duration, "outro", 0.3, 0.0),
        ]

    chunks[0].label = "intro"
    chunks[-1].label = "outro"
    if len(chunks) > 2:
        max_idx = int(np.argmax([c.energy for c in chunks[1:-1]])) + 1
        chunks[max_idx].label = "chorus"
        for idx, sec in enumerate(chunks[1:-1], start=1):
            if idx != max_idx:
                sec.label = "verse" if sec.energy > 0.2 else "breakdown"
    return chunks
