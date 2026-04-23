"""Tests for neural embedding wrappers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import torch

from pyromind.audio.embeddings import CLAPEmbedder, MERTEmbedder
from pyromind.audio.loader import load_audio, to_mono


class _FakeTensor(dict):
    def to(self, device: str):  # noqa: ARG002
        return self


class _FakeProcessor:
    def __call__(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return {"input_values": torch.ones((1, 160))}


class _FakeModelOutput:
    def __init__(self, dim: int) -> None:
        self.last_hidden_state = torch.ones((1, 4, dim))


class _FakeModel:
    def __init__(self, dim: int) -> None:
        self.dim = dim
        self.moves: list[str] = []

    def to(self, device: str):
        self.moves.append(device)
        return self

    def __call__(self, **kwargs):  # noqa: ANN003
        return _FakeModelOutput(self.dim)


def test_mert_embeddings(monkeypatch: pytest.MonkeyPatch, sine_fixture: Path) -> None:
    fake_model = _FakeModel(768)
    monkeypatch.setattr("transformers.AutoProcessor.from_pretrained", lambda *a, **k: _FakeProcessor())
    monkeypatch.setattr("transformers.AutoModel.from_pretrained", lambda *a, **k: fake_model)
    monkeypatch.setattr("torch.cuda.is_available", lambda: False)
    audio, sr = load_audio(sine_fixture)
    rows = MERTEmbedder().extract(to_mono(audio), sr, window_s=2.0, hop_s=1.0)
    assert len(rows) > 0
    assert len(rows[0][1]) == 768
    assert fake_model.moves[-1] == "cpu"


def test_clap_embeddings(monkeypatch: pytest.MonkeyPatch, sine_fixture: Path) -> None:
    fake_model = _FakeModel(512)
    monkeypatch.setattr("transformers.AutoProcessor.from_pretrained", lambda *a, **k: _FakeProcessor())
    monkeypatch.setattr("transformers.AutoModel.from_pretrained", lambda *a, **k: fake_model)
    monkeypatch.setattr("torch.cuda.is_available", lambda: False)
    audio, sr = load_audio(sine_fixture)
    rows = CLAPEmbedder().extract(to_mono(audio), sr, window_s=2.0)
    assert len(rows) > 0
    assert len(rows[0][1]) == 512
    assert fake_model.moves[-1] == "cpu"
