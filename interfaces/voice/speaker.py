"""Audio playback ? real (sounddevice) and fake (test) implementations."""

from __future__ import annotations

from typing import Protocol

from core.log import get_logger
from interfaces.voice.audio import AudioOutput
from interfaces.voice.errors import PlaybackError

logger = get_logger(__name__)


class SpeakerProtocol(Protocol):
    def play(self, audio: AudioOutput) -> None: ...


class Speaker:
    """Blocking audio playback via ``sounddevice``.

    Import of the audio library is deferred so a base NAV install can still
    import this module.
    """

    def play(self, audio: AudioOutput) -> None:
        try:
            import sounddevice as sd  # type: ignore[import-not-found,import-untyped]
        except ImportError as exc:
            raise PlaybackError(
                'sounddevice not installed. Install voice extras: pip install -e ".[voice]"'
            ) from exc

        logger.info("Speaker playing audio (rate=%d)", audio.sample_rate)
        try:
            sd.play(audio.samples, samplerate=audio.sample_rate)
            sd.wait()
        except Exception as exc:  # noqa: BLE001
            raise PlaybackError(f"Audio playback failed: {exc}") from exc


class FakeSpeaker:
    """Test speaker that records what it was asked to play."""

    def __init__(self) -> None:
        self.played: list[AudioOutput] = []

    def play(self, audio: AudioOutput) -> None:
        self.played.append(audio)


__all__ = ["Speaker", "FakeSpeaker", "SpeakerProtocol"]
