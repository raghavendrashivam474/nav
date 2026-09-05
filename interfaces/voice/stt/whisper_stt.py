"""Whisper speech-to-text implementation — S4 voice boundary.

Uses faster-whisper for local, fast CPU/GPU inference.
Forces language="en" by default to prevent multilingual mis-detections.
"""

from __future__ import annotations

from typing import Any

from core.log import get_logger
from interfaces.voice.audio import AudioInput
from interfaces.voice.contracts import SpeechToText
from interfaces.voice.errors import ConfigurationError, STTError

logger = get_logger(__name__)


class WhisperSTT(SpeechToText):
    """Speech-to-text using local faster-whisper."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "en",
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._language = language
        self._model: Any = None

    @property
    def name(self) -> str:
        return f"whisper-{self._model_size}"

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found,import-untyped]
        except ImportError as exc:
            raise ConfigurationError(
                'faster-whisper is not installed. Install voice extras: pip install -e ".[voice]"'
            ) from exc

        logger.info("Loading Whisper model: %s", self._model_size)
        try:
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
        except Exception as exc:
            raise ConfigurationError(f"Failed to load Whisper model: {exc}") from exc

    def transcribe(self, audio: AudioInput) -> str:
        self._ensure_model()
        try:
            import numpy as np  # type: ignore[import-not-found,import-untyped]
        except ImportError as exc:
            raise ConfigurationError(
                'numpy is not installed. Install voice extras: pip install -e ".[voice]"'
            ) from exc

        samples = audio.samples
        if isinstance(samples, bytes):
            samples = np.frombuffer(samples, dtype=np.float32)
        elif not isinstance(samples, np.ndarray):
            samples = np.array(samples, dtype=np.float32)

        if samples.dtype != np.float32:
            samples = samples.astype(np.float32)

        logger.info(
            "Whisper transcribing (%d samples @ %d Hz, lang=%s)",
            len(samples),
            audio.sample_rate,
            self._language,
        )

        try:
            segments, info = self._model.transcribe(
                samples,
                beam_size=5,
                language=self._language,
                vad_filter=True,
            )
            text = " ".join(s.text.strip() for s in segments).strip()
            logger.info("Whisper transcript length: %d chars", len(text))
            return text
        except Exception as exc:
            raise STTError(f"Whisper transcription failed: {exc}") from exc
