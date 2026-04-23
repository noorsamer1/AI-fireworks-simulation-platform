"""Feature extraction for beats, onsets, tonal info, and mood proxies."""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np


def _tempo_to_float(tempo: float | np.ndarray) -> float:
    """Normalize librosa tempo output to a plain float."""
    if isinstance(tempo, np.ndarray):
        if tempo.size == 0:
            return 0.0
        return float(tempo.reshape(-1)[0])
    return float(tempo)


def detect_beats(audio: np.ndarray, sr: int) -> tuple[float, list[float], list[float]]:
    """Return tempo BPM, beat times, and downbeat times."""
    tempo, beat_frames = librosa.beat.beat_track(y=audio, sr=sr)
    beats = librosa.frames_to_time(beat_frames, sr=sr).tolist()
    downbeats: list[float]
    try:
        from madmom.features.downbeats import DBNDownBeatTrackingProcessor, RNNDownBeatProcessor

        activations = RNNDownBeatProcessor()(audio)
        downbeat_data = DBNDownBeatTrackingProcessor(beats_per_bar=[4], fps=100)(activations)
        downbeats = [float(item[0]) for item in downbeat_data if int(item[1]) == 1]
    except Exception:  # noqa: BLE001
        downbeats = beats[::4]
    return _tempo_to_float(tempo), [float(x) for x in beats], downbeats


def detect_tempo_curve(audio: np.ndarray, sr: int, hop_length: int = 512) -> list[tuple[float, float]]:
    """Estimate local tempo in 1-second windows."""
    window = sr
    curve: list[tuple[float, float]] = []
    for start in range(0, max(len(audio) - window, 1), window):
        chunk = audio[start : start + window]
        if len(chunk) < hop_length:
            continue
        tempo, _ = librosa.beat.beat_track(y=chunk, sr=sr, hop_length=hop_length)
        curve.append((float(start / sr), _tempo_to_float(tempo)))
    return curve


def detect_onsets(audio: np.ndarray, sr: int) -> list[float]:
    """Detect onset timestamps in seconds."""
    onset_frames = librosa.onset.onset_detect(y=audio, sr=sr, backtrack=True)
    return [float(x) for x in librosa.frames_to_time(onset_frames, sr=sr)]


def detect_per_stem_onsets(stem_paths: dict[str, Path]) -> dict[str, list[float]]:
    """Run onset detection for each stem."""
    result: dict[str, list[float]] = {}
    for stem, path in stem_paths.items():
        audio, sr = librosa.load(path, sr=None, mono=True)
        result[stem] = detect_onsets(audio, sr)
    return result


def extract_key_mode(audio: np.ndarray, sr: int) -> tuple[str, str]:
    """Estimate key and mode with a simple K-S chroma profile."""
    chroma = librosa.feature.chroma_cqt(y=audio, sr=sr)
    profile = np.mean(chroma, axis=1)
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    best_score = -np.inf
    best_key = 0
    best_mode = "major"
    for key in range(12):
        major_score = np.corrcoef(profile, np.roll(major_profile, key))[0, 1]
        minor_score = np.corrcoef(profile, np.roll(minor_profile, key))[0, 1]
        if major_score > best_score:
            best_score = major_score
            best_key = key
            best_mode = "major"
        if minor_score > best_score:
            best_score = minor_score
            best_key = key
            best_mode = "minor"
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return names[best_key], best_mode


def extract_loudness_curve(audio: np.ndarray, sr: int, resolution_hz: int = 100) -> list[float]:
    """Return RMS loudness curve sampled at fixed resolution."""
    frame_length = max(int(sr / resolution_hz), 1)
    hop_length = frame_length
    rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]
    return [float(v) for v in rms]


def extract_spectral_centroid_curve(audio: np.ndarray, sr: int) -> list[float]:
    """Return spectral centroid curve."""
    centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
    return [float(v) for v in centroid]


def extract_mood(audio: np.ndarray, sr: int) -> list[float]:
    """Extract a 10-dimensional mood vector, with safe fallback."""
    try:
        import essentia.standard as es

        extractor = es.MusicExtractor()
        features, _ = extractor(audio)
        values = [float(features.get(f"lowlevel.mfcc.mean.{i}", 0.0)) for i in range(10)]
        norm = np.array(values, dtype=np.float32)
        max_abs = float(np.max(np.abs(norm))) if norm.size else 1.0
        if max_abs == 0:
            return [0.0] * 10
        scaled = np.clip((norm / max_abs + 1) / 2, 0, 1)
        return [float(v) for v in scaled]
    except Exception:  # noqa: BLE001
        return [0.0] * 10
