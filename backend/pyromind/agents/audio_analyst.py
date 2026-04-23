"""AudioAnalystAgent LangGraph node."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import soundfile as sf

import pyromind.config as _pm_config
from pyromind.agents.base import agent_node
from pyromind.audio.embeddings import CLAPEmbedder, MERTEmbedder
from pyromind.audio.features import (
    detect_beats,
    detect_onsets,
    detect_per_stem_onsets,
    detect_tempo_curve,
    extract_key_mode,
    extract_loudness_curve,
    extract_mood,
    extract_spectral_centroid_curve,
)
from pyromind.audio.loader import compute_sha256, load_audio, normalize_lufs, resample, to_mono
from pyromind.audio.sections import segment_audio
from pyromind.audio.separation import DemucsWrapper
from pyromind.graph.state import ShowState
from pyromind.models.audio import AudioAnalysis, Section


def _fallback_stems(audio: np.ndarray, sr: int, cache_dir: Path) -> dict[str, Path]:
    """Write deterministic placeholder stems when Demucs is unavailable."""
    stem_dir = cache_dir / "stems"
    stem_dir.mkdir(parents=True, exist_ok=True)
    stems = {
        "drums": stem_dir / "drums.wav",
        "bass": stem_dir / "bass.wav",
        "vocals": stem_dir / "vocals.wav",
        "other": stem_dir / "other.wav",
    }
    for path in stems.values():
        if not path.exists():
            sf.write(path, audio, sr)
    return stems


def _cuda_empty_cache() -> None:
    """Clear CUDA cache when torch is installed and CUDA is active."""
    try:
        import torch  # noqa: PLC0415

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:  # noqa: BLE001
        return


def _audio_analyst_impl(state: ShowState) -> ShowState:
    """Populate ``state['audio']`` from source audio."""
    song_path = Path(state["song_path"])
    cache_root = Path(_pm_config.settings.audio_cache_dir)
    sha = compute_sha256(song_path)
    cache_dir = cache_root / sha
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "analysis.json"
    if cache_file.exists():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        return {**state, "audio": AudioAnalysis.model_validate(cached)}

    audio, sr = load_audio(song_path)
    audio = normalize_lufs(audio, sr)
    audio = to_mono(audio)
    audio, sr = resample(audio, sr)

    try:
        stems = DemucsWrapper().separate(song_path, cache_root)
    except Exception:  # noqa: BLE001
        stems = _fallback_stems(audio, sr, cache_dir)
    tempo_bpm, beats, downbeats = detect_beats(audio, sr)
    onsets = detect_onsets(audio, sr)
    _ = detect_per_stem_onsets(stems)
    key, mode = extract_key_mode(audio, sr)
    loudness = extract_loudness_curve(audio, sr)
    centroid = extract_spectral_centroid_curve(audio, sr)
    mood = extract_mood(audio, sr)

    mert_embeddings = MERTEmbedder().extract(audio, sr)
    _cuda_empty_cache()
    sections_raw = segment_audio(audio, sr, mert_embeddings=mert_embeddings)
    clap_embeddings = CLAPEmbedder().extract(audio, sr)
    _cuda_empty_cache()

    analysis = AudioAnalysis(
        duration_s=float(len(audio) / sr),
        sample_rate=sr,
        tempo_bpm=tempo_bpm,
        tempo_curve=detect_tempo_curve(audio, sr),
        beats_s=beats,
        downbeats_s=downbeats,
        onsets_s=onsets,
        key=key,
        mode=mode,
        loudness_curve=loudness,
        spectral_centroid_curve=centroid,
        stems={k: str(v) for k, v in stems.items()},
        sections=[Section(**section.__dict__) for section in sections_raw],
        mood_vector=mood,
        mert_embedding=[v for _, vec in mert_embeddings for v in vec],
        clap_embeddings=clap_embeddings,
    )
    cache_file.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")
    return {**state, "audio": analysis}


@agent_node("audio_analyst")
def audio_analyst_node(state: ShowState) -> ShowState:
    """Populate ``state['audio']`` from source audio (failures become ``agent_failed`` events)."""
    return _audio_analyst_impl(state)
