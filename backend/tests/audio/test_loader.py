"""Unit tests for audio loading utilities."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from pyromind.audio.loader import compute_sha256, load_audio, normalize_lufs, resample, to_mono


def test_load_audio(sine_fixture: Path) -> None:
    audio, sr = load_audio(sine_fixture)
    assert sr == 44_100
    assert audio.ndim == 2


def test_normalize_lufs(sine_fixture: Path) -> None:
    audio, sr = load_audio(sine_fixture)
    norm = normalize_lufs(audio, sr)
    assert norm.shape == audio.shape


def test_to_mono(sine_fixture: Path) -> None:
    audio, _ = load_audio(sine_fixture)
    mono = to_mono(audio)
    assert mono.ndim == 1
    assert mono.shape[0] == audio.shape[0]


def test_sha256_consistency(sine_fixture: Path) -> None:
    digest_a = compute_sha256(sine_fixture)
    digest_b = compute_sha256(sine_fixture)
    assert digest_a == digest_b


def test_resample(sine_fixture: Path) -> None:
    audio, sr = load_audio(sine_fixture)
    mono = to_mono(audio)
    out, out_sr = resample(mono, sr, target_sr=22_050)
    assert out_sr == 22_050
    assert out.shape[0] > 0
