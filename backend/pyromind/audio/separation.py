"""Demucs stem separation wrapper with VRAM-safe model lifecycle."""

from __future__ import annotations

from pathlib import Path

try:
    import torch
except ModuleNotFoundError:  # pragma: no cover - exercised in dependency-missing environments
    torch = None

import pyromind.config as _pm_config
from pyromind.audio.loader import compute_sha256

STEMS = ["drums", "bass", "vocals", "other"]


class DemucsWrapper:
    """Demucs separator that always offloads the model after each run."""

    def __init__(self) -> None:
        self._model = None
        self._separator = None

    def separate(self, audio_path: str | Path, output_dir: str | Path) -> dict[str, Path]:
        """Separate source audio into 4 stems and return generated file paths."""
        audio_path = Path(audio_path)
        output_dir = Path(output_dir)
        cache_key = compute_sha256(audio_path)
        stem_dir = output_dir / cache_key / "stems"
        stem_dir.mkdir(parents=True, exist_ok=True)
        cached = {stem: stem_dir / f"{stem}.wav" for stem in STEMS}
        if all(path.exists() for path in cached.values()):
            return cached

        self._load_model()
        try:
            if self._separator is None:
                raise RuntimeError("Demucs separator is not initialized.")
            self._separator.separate_audio_file(str(audio_path), str(stem_dir))
            return cached
        finally:
            self._offload_model()

    def _load_model(self) -> None:
        """Load Demucs separator to preferred device."""
        model_name = _pm_config.settings.demucs_model
        if model_name == "htdemucs_6s":
            model_name = "htdemucs"
        device = _pm_config.settings.audio_device
        if device == "cuda" and (torch is None or not torch.cuda.is_available()):
            device = "cpu"
        try:
            from demucs.api import Separator

            self._separator = Separator(model=model_name, device=device)
            self._model = self._separator.model
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("Failed to load Demucs separator.") from exc

    def _offload_model(self) -> None:
        """Move model to CPU and clear CUDA cache."""
        if self._model is not None and hasattr(self._model, "to"):
            self._model.to("cpu")
        self._model = None
        self._separator = None
        if torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()
