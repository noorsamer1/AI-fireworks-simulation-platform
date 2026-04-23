"""Tests for structural segmentation."""

from __future__ import annotations

from pathlib import Path

from pyromind.audio.loader import load_audio, to_mono
from pyromind.audio.sections import segment_audio


def test_segment_audio_labels(sine_fixture: Path) -> None:
    audio, sr = load_audio(sine_fixture)
    sections = segment_audio(to_mono(audio), sr)
    assert len(sections) >= 2
    assert sections[0].label == "intro"
    assert sections[-1].label == "outro"
    assert all((section.end_s - section.start_s) >= 10 for section in sections)
