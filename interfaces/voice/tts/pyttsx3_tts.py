"""Local text-to-speech via pyttsx3 (OS-native voices, offline, no key).

pyttsx3 speaks directly through the OS audio stack rather than returning a
buffer, so this adapter marks the AudioOutput as ``self_played=True`` in
metadata and the VoiceInterface knows not to hand it to the Speaker.

This keeps the abstraction honest: the TTS provider owns synthesis,
optionally owns playback, and the AudioOutput carries the truth about
what still needs to happen.
"""

from __future__ import annotations

from typing import Any

from core.log import get_logger
from interfaces.voice.audio import AudioOutput
from interfaces.voice.contracts import TextToSpeech
from interfaces.voice.errors import ConfigurationError, TTSError

logger = get_logger(__name__)


class Pyttsx3TTS(TextToSpeech):
    """Offline TTS using the operating system's native voice engine."""

    def __init__(self) -> None:
        self._engine: Any | None = None

    @property
    def name(self) -> str:
        return "pyttsx3"

    def _load_engine(self) -> Any:
        if self._engine is not None:
            return self._engine
        try:
            import pyttsx3  # type: ignore[import-not-found,import-untyped]
        except ImportError as exc:
            raise ConfigurationError(
                'pyttsx3 not installed. Install voice extras: pip install -e ".[voice]"'
            ) from exc

        try:
            self._engine = pyttsx3.init()
        except Exception as exc:  # noqa: BLE001
            raise TTSError(f"Failed to initialize pyttsx3 engine: {exc}") from exc
        return self._engine

    def synthesize(self, text: str) -> AudioOutput:
        engine = self._load_engine()
        logger.info("pyttsx3 speaking (%d chars)", len(text))

        try:
            engine.say(text)
            engine.runAndWait()
        except Exception as exc:  # noqa: BLE001
            raise TTSError(f"pyttsx3 synthesis failed: {exc}") from exc

        # pyttsx3 has already produced sound directly. Return a marker
        # AudioOutput so the Speaker knows there's nothing left to play.
        return AudioOutput(
            samples=b"",
            sample_rate=0,
            channels=1,
            metadata={"self_played": True, "source_text": text},
        )
