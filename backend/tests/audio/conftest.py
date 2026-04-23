"""Audio test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")


@pytest.fixture()
def sine_fixture(tmp_path: Path) -> Path:
    """Generate a 3-minute stereo synthetic waveform with changing frequencies."""
    sr = 44_100
    duration = 180
    t = np.linspace(0, duration, duration * sr, endpoint=False)
    section_len = 45 * sr
    freq = np.zeros_like(t)
    freq[:section_len] = 110.0
    freq[section_len : 2 * section_len] = 220.0
    freq[2 * section_len : 3 * section_len] = 440.0
    freq[3 * section_len :] = 220.0
    wave = 0.25 * np.sin(2 * np.pi * freq * t, dtype=np.float32)
    stereo = np.stack([wave, wave], axis=1)
    path = tmp_path / "synthetic.wav"
    sf.write(path, stereo, sr)
    return path
