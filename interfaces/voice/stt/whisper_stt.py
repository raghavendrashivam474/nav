"""Local Whisper STT via ``faster-whisper``.

The heavy import is deferred until first transcription so a base NAV install
can import ``interfaces.voice`` without the voice extras.
"""

from __future__ import annotations

import os
from typing import Any

from core.log import get_logger
from interfaces.voice.audio import AudioInput
from interfaces.voice.contracts import SpeechToText
from interfaces.voice.errors import ConfigurationError, STTError

logger = get_logger(__name__)


class WhisperSTT(SpeechToText):
    """Local speech-to-text using faster-whisper.

    Model is loaded lazily on first call to avoid startup cost when voice
    is imported but unused.
    """

    def __init__(self, model_size: str | None = None) -> None:
        self._model_size = model_size or os.environ.get("NAV_WHISPER_MODEL", "base")
        self._model: Any | None = None

    @property
    def name(self) -> str:
        return f"whisper:{self._model_size}"

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found,import-untyped]
        except ImportError as exc:
            raise ConfigurationError(
                'faster-whisper not installed. Install voice extras: pip install -e ".[voice]"'
            ) from exc

        logger.info("Loading Whisper model: %s", self._model_size)
        try:
            self._model = WhisperModel(self._model_size, device="cpu", compute_type="int8")
        except Exception as exc:  # noqa: BLE001
            raise STTError(f"Failed to load Whisper model '{self._model_size}': {exc}") from exc
        return self._model

    def transcribe(self, audio: AudioInput) -> str:
        model = self._load_model()

        try:
            import numpy as np  # type: ignore[import-not-found,import-untyped]
        except ImportError as exc:
            raise ConfigurationError("numpy not installed with voice extras.") from exc

        # faster-whisper expects mono float32 numpy at 16 kHz.
        samples = audio.samples
        if not isinstance(samples, np.ndarray):
            try:
                samples = np.asarray(samples, dtype=np.float32)
            except Exception as exc:  # noqa: BLE001
                raise STTError(f"Cannot convert audio samples to numpy: {exc}") from exc

        if samples.ndim > 1:
            samples = samples.mean(axis=1).astype(np.float32)

        logger.info(
            "Whisper transcribing (%d samples @ %d Hz)",
            samples.shape[0],
            audio.sample_rate,
        )

        try:
            segments, _info = model.transcribe(samples, beam_size=1)
            text = " ".join(seg.text.strip() for seg in segments).strip()
        except Exception as exc:  # noqa: BLE001
            raise STTError(f"Whisper transcription failed: {exc}") from exc

        logger.info("Whisper transcript length: %d chars", len(text))
        return text
