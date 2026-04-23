"""Tests for feature extraction helpers."""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np
import pytest
import soundfile as sf

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
from pyromind.audio.loader import load_audio, to_mono


def test_detect_beats(sine_fixture: Path) -> None:
    audio, sr = load_audio(sine_fixture)
    tempo, beats, downbeats = detect_beats(to_mono(audio), sr)
    assert tempo >= 0
    assert isinstance(beats, list)
    assert isinstance(downbeats, list)


def test_detect_tempo_curve(sine_fixture: Path) -> None:
    audio, sr = load_audio(sine_fixture)
    curve = detect_tempo_curve(to_mono(audio), sr)
    assert len(curve) > 0


def test_detect_onsets(sine_fixture: Path) -> None:
    audio, sr = load_audio(sine_fixture)
    onsets = detect_onsets(to_mono(audio), sr)
    assert isinstance(onsets, list)


def test_detect_per_stem_onsets(tmp_path: Path, sine_fixture: Path) -> None:
    stems = {}
    audio, sr = librosa.load(sine_fixture, sr=None, mono=True)
    for stem in ("drums", "bass", "vocals", "other"):
        stem_path = tmp_path / f"{stem}.wav"
        sf.write(stem_path, audio, sr)
        stems[stem] = stem_path
    result = detect_per_stem_onsets(stems)
    assert set(result.keys()) == {"drums", "bass", "vocals", "other"}


def test_extract_key_mode(sine_fixture: Path) -> None:
    audio, sr = load_audio(sine_fixture)
    key, mode = extract_key_mode(to_mono(audio), sr)
    assert isinstance(key, str)
    assert mode in {"major", "minor"}


def test_extract_curves_and_mood(sine_fixture: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    audio, sr = load_audio(sine_fixture)
    mono = to_mono(audio)
    assert len(extract_loudness_curve(mono, sr)) > 0
    assert len(extract_spectral_centroid_curve(mono, sr)) > 0
    monkeypatch.setitem(__import__("sys").modules, "essentia", None)
    mood = extract_mood(mono, sr)
    assert len(mood) == 10
