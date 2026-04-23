"""Audio loading, validation, and normalization."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}
TARGET_LUFS = -14.0
TARGET_SR = 44100


def load_audio(path: str | Path) -> tuple[np.ndarray, int]:
    """Load audio file and return (samples, sample_rate)."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")
    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported audio format: {file_path.suffix}")
    try:
        audio, sr = sf.read(str(file_path), always_2d=False, dtype="float32")
    except RuntimeError as exc:
        raise ValueError(f"Failed to decode audio file: {file_path}") from exc
    if audio.size == 0:
        raise ValueError(f"Audio file is empty: {file_path}")
    return np.asarray(audio, dtype=np.float32), int(sr)


def normalize_lufs(audio: np.ndarray, sr: int, target_lufs: float = TARGET_LUFS) -> np.ndarray:
    """Normalize audio using RMS-to-LUFS approximation."""
    del sr  # The approximation does not depend on sample rate.
    rms = float(np.sqrt(np.mean(np.square(audio))) + 1e-12)
    current_lufs = 20 * np.log10(rms)
    gain_db = target_lufs - current_lufs
    gain = float(10 ** (gain_db / 20))
    normalized = audio * gain
    return np.clip(normalized, -1.0, 1.0).astype(np.float32)


def to_mono(audio: np.ndarray) -> np.ndarray:
    """Convert multi-channel audio to mono."""
    if audio.ndim == 1:
        return audio.astype(np.float32)
    if audio.ndim == 2:
        return np.mean(audio, axis=1, dtype=np.float32)
    raise ValueError("Audio array must be 1D or 2D.")


def compute_sha256(path: str | Path) -> str:
    """Return SHA256 hash for audio file bytes."""
    file_path = Path(path)
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resample(audio: np.ndarray, sr: int, target_sr: int = TARGET_SR) -> tuple[np.ndarray, int]:
    """Resample audio to target sample rate."""
    if sr == target_sr:
        return audio.astype(np.float32), sr
    if audio.ndim == 1:
        output_len = int(round(len(audio) * target_sr / sr))
        out = signal.resample(audio, output_len).astype(np.float32)
        return out, target_sr
    output_len = int(round(audio.shape[0] * target_sr / sr))
    out = signal.resample(audio, output_len, axis=0).astype(np.float32)
    return out, target_sr
