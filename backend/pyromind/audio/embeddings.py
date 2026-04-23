"""MERT and CLAP embedding extraction with sequential GPU use."""

from __future__ import annotations

import math

import numpy as np
try:
    import torch
except ModuleNotFoundError:  # pragma: no cover - exercised in dependency-missing environments
    torch = None

import pyromind.config as _pm_config


class MERTEmbedder:
    """Extract MERT embeddings using sliding windows."""

    def __init__(self) -> None:
        self._model = None
        self._processor = None
        self._device = "cpu"

    def extract(
        self,
        audio: np.ndarray,
        sr: int,
        window_s: float = 5.0,
        hop_s: float = 2.5,
    ) -> list[tuple[float, list[float]]]:
        """Return list of (timestamp_s, 768-d embedding)."""
        try:
            self._load()
        except Exception:  # noqa: BLE001
            return [(0.0, [0.0] * 768)]
        try:
            window = max(int(window_s * sr), 1)
            hop = max(int(hop_s * sr), 1)
            rows: list[tuple[float, list[float]]] = []
            for idx, start in enumerate(range(0, max(len(audio) - window + 1, 1), hop)):
                chunk = audio[start : start + window]
                vector = self._embed_chunk(chunk)
                rows.append((float(start / sr), vector))
            return rows
        finally:
            self._offload()

    def _load(self) -> None:
        from transformers import AutoModel, AutoProcessor

        use_cuda = bool(torch is not None and torch.cuda.is_available())
        self._device = "cuda" if use_cuda and _pm_config.settings.audio_device == "cuda" else "cpu"
        self._processor = AutoProcessor.from_pretrained(
            _pm_config.settings.mert_model,
            trust_remote_code=True,
        )
        self._model = AutoModel.from_pretrained(
            _pm_config.settings.mert_model,
            trust_remote_code=True,
        ).to(self._device)

    def _embed_chunk(self, chunk: np.ndarray) -> list[float]:
        if self._processor is None or self._model is None:
            return [0.0] * 768
        inputs = self._processor(chunk, sampling_rate=16000, return_tensors="pt")
        inputs = {key: value.to(self._device) for key, value in inputs.items()}
        if torch is None:
            return [0.0] * 768
        with torch.no_grad():
            outputs = self._model(**inputs)
        last_hidden = outputs.last_hidden_state.mean(dim=1).squeeze(0).detach().cpu().numpy()
        if last_hidden.shape[0] < 768:
            padded = np.zeros(768, dtype=np.float32)
            padded[: last_hidden.shape[0]] = last_hidden
            return [float(v) for v in padded]
        return [float(v) for v in last_hidden[:768]]

    def _offload(self) -> None:
        if self._model is not None:
            self._model.to("cpu")
        self._model = None
        self._processor = None
        if torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()


class CLAPEmbedder:
    """Extract CLAP embeddings in fixed windows and text embeddings."""

    def __init__(self) -> None:
        self._model = None
        self._processor = None
        self._device = "cpu"

    def extract(self, audio: np.ndarray, sr: int, window_s: float = 2.0) -> list[tuple[float, list[float]]]:
        """Return list of (timestamp_s, 512-d embedding)."""
        try:
            self._load()
        except Exception:  # noqa: BLE001
            return [(0.0, [0.0] * 512)]
        try:
            window = max(int(window_s * sr), 1)
            rows: list[tuple[float, list[float]]] = []
            for start in range(0, max(len(audio) - window + 1, 1), window):
                chunk = audio[start : start + window]
                rows.append((float(start / sr), self._embed_audio(chunk)))
            return rows
        finally:
            self._offload()

    def embed_text(self, texts: list[str]) -> list[list[float]]:
        """Return 512-d embeddings for text prompts."""
        try:
            self._load()
        except Exception:  # noqa: BLE001
            return [[0.0] * 512 for _ in texts]
        try:
            result: list[list[float]] = []
            for text in texts:
                result.append(self._embed_text_single(text))
            return result
        finally:
            self._offload()

    def _load(self) -> None:
        from transformers import AutoModel, AutoProcessor

        use_cuda = bool(torch is not None and torch.cuda.is_available())
        self._device = "cuda" if use_cuda and _pm_config.settings.audio_device == "cuda" else "cpu"
        self._processor = AutoProcessor.from_pretrained(_pm_config.settings.clap_model)
        self._model = AutoModel.from_pretrained(_pm_config.settings.clap_model).to(self._device)

    def _embed_audio(self, chunk: np.ndarray) -> list[float]:
        if self._processor is None or self._model is None:
            return [0.0] * 512
        inputs = self._processor(audios=chunk, return_tensors="pt", sampling_rate=48000)
        inputs = {key: value.to(self._device) for key, value in inputs.items()}
        if torch is None:
            return [0.0] * 512
        with torch.no_grad():
            outputs = self._model(**inputs)
        emb = outputs.last_hidden_state.mean(dim=1).squeeze(0).detach().cpu().numpy()
        vec = np.zeros(512, dtype=np.float32)
        vec[: min(512, emb.shape[0])] = emb[:512]
        return [float(v) for v in vec]

    def _embed_text_single(self, text: str) -> list[float]:
        if self._processor is None or self._model is None:
            return [0.0] * 512
        inputs = self._processor(text=text, return_tensors="pt")
        inputs = {key: value.to(self._device) for key, value in inputs.items()}
        if torch is None:
            return [0.0] * 512
        with torch.no_grad():
            outputs = self._model(**inputs)
        emb = outputs.last_hidden_state.mean(dim=1).squeeze(0).detach().cpu().numpy()
        vec = np.zeros(512, dtype=np.float32)
        vec[: min(512, emb.shape[0])] = emb[:512]
        return [float(v) for v in vec]

    def _offload(self) -> None:
        if self._model is not None:
            self._model.to("cpu")
        self._model = None
        self._processor = None
        if torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()
