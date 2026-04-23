"""Tests for Demucs separation wrapper."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyromind.audio.separation import DemucsWrapper, STEMS


class _FakeModel:
    def __init__(self) -> None:
        self.moves: list[str] = []

    def to(self, device: str):  # noqa: ANN001
        self.moves.append(device)
        return self


class _FakeSeparator:
    def __init__(self, model: str, device: str) -> None:  # noqa: ARG002
        self.model = _FakeModel()

    def separate_audio_file(self, audio_path: str, stem_dir: str) -> None:
        for stem in STEMS:
            Path(stem_dir, f"{stem}.wav").write_bytes(b"stub")


def test_separation_cache_hit(sine_fixture: Path, tmp_path: Path) -> None:
    cache_key = __import__("hashlib").sha256(sine_fixture.read_bytes()).hexdigest()
    stem_dir = tmp_path / cache_key / "stems"
    stem_dir.mkdir(parents=True, exist_ok=True)
    for stem in STEMS:
        (stem_dir / f"{stem}.wav").write_bytes(b"x")
    result = DemucsWrapper().separate(sine_fixture, tmp_path)
    assert set(result.keys()) == set(STEMS)


def test_separation_cache_miss(monkeypatch: pytest.MonkeyPatch, sine_fixture: Path, tmp_path: Path) -> None:
    def fake_load(self):  # noqa: ANN001
        self._separator = _FakeSeparator("htdemucs", "cpu")
        self._model = self._separator.model

    monkeypatch.setattr(DemucsWrapper, "_load_model", fake_load)
    monkeypatch.setattr("torch.cuda.is_available", lambda: False)
    wrapper = DemucsWrapper()
    result = wrapper.separate(sine_fixture, tmp_path)
    assert set(result.keys()) == set(STEMS)
    assert all(path.exists() for path in result.values())
