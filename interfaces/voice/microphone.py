"""Microphone capture ? press-to-talk model.

The real ``Microphone`` uses ``sounddevice`` (optional dependency) but its
import is deferred to ``record()`` so this module can be imported on a
base NAV install without the voice extras. Tests use ``FakeMicrophone``
and require zero audio hardware or dependencies.
"""

from __future__ import annotations

from typing import Protocol

from core.log import get_logger
from interfaces.voice.audio import AudioInput
from interfaces.voice.errors import MicrophoneError

logger = get_logger(__name__)


class MicrophoneProtocol(Protocol):
    """Structural type ? anything with ``record()`` is a microphone."""

    def record(self, max_seconds: float) -> AudioInput: ...


class Microphone:
    """Blocking press-to-talk microphone capture via ``sounddevice``.

    Records a fixed-duration mono PCM buffer at ``sample_rate`` Hz. Intended
    for the S4 explicit-activation model ? no VAD, no streaming, no wake word.
    """

    def __init__(self, sample_rate: int = 16000, channels: int = 1) -> None:
        self._sample_rate = sample_rate
        self._channels = channels

    def record(self, max_seconds: float) -> AudioInput:
        try:
            import numpy as np  # type: ignore[import-not-found,import-untyped]
            import sounddevice as sd  # type: ignore[import-not-found,import-untyped]
        except ImportError as exc:
            raise MicrophoneError(
                "sounddevice/numpy not installed. Install the voice extras: "
                'pip install -e ".[voice]"'
            ) from exc

        logger.info(
            "Microphone recording (max_seconds=%.1f, rate=%d)",
            max_seconds,
            self._sample_rate,
        )

        try:
            frames = int(max_seconds * self._sample_rate)
            samples = sd.rec(
                frames,
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype="float32",
            )
            sd.wait()
        except Exception as exc:
            raise MicrophoneError(f"Microphone capture failed: {exc}") from exc

        if samples is None or (hasattr(samples, "size") and samples.size == 0):
            raise MicrophoneError("Microphone returned an empty buffer.")

        # Detect near-silence so callers can fail fast rather than send silence
        # into the STT provider.
        rms = float(np.sqrt(np.mean(np.square(samples))))
        if rms < 1e-4:
            raise MicrophoneError("No speech detected (recording was silent).")

        duration = float(len(samples)) / self._sample_rate
        logger.info("Microphone captured %.2fs of audio (rms=%.4f)", duration, rms)

        return AudioInput(
            samples=samples,
            sample_rate=self._sample_rate,
            channels=self._channels,
            duration_seconds=duration,
        )


class FakeMicrophone:
    """Deterministic microphone for tests.

    Returns a pre-configured ``AudioInput`` on ``record()``. Can also be
    configured to raise a ``MicrophoneError`` to simulate hardware failures.
    """

    def __init__(
        self,
        audio: AudioInput | None = None,
        *,
        raise_error: MicrophoneError | None = None,
    ) -> None:
        self._audio = audio or AudioInput(
            samples=b"\x00" * 1024,
            sample_rate=16000,
            channels=1,
            duration_seconds=1.0,
        )
        self._raise_error = raise_error
        self.record_calls: list[float] = []

    def record(self, max_seconds: float) -> AudioInput:
        self.record_calls.append(max_seconds)
        if self._raise_error is not None:
            raise self._raise_error
        return self._audio


__all__ = ["Microphone", "FakeMicrophone", "MicrophoneProtocol"]
