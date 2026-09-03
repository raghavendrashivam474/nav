"""Speech-to-text and text-to-speech abstract contracts.

The rest of NAV depends only on these interfaces. Concrete providers
(Whisper, pyttsx3, cloud APIs, future engines) live behind these ABCs
so they can be swapped without touching Core, Cognition, or the
VoiceInterface orchestration logic.

This mirrors the S3 AIGateway pattern.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from interfaces.voice.audio import AudioInput, AudioOutput


class SpeechToText(ABC):
    """Convert captured audio into text."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name, for logging only."""

    @abstractmethod
    def transcribe(self, audio: AudioInput) -> str:
        """Transcribe ``audio`` into a UTF-8 string.

        Raises:
            interfaces.voice.errors.STTError: On any transcription failure.
        """


class TextToSpeech(ABC):
    """Convert text into synthesized audio."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name, for logging only."""

    @abstractmethod
    def synthesize(self, text: str) -> AudioOutput:
        """Synthesize ``text`` into an ``AudioOutput``.

        Raises:
            interfaces.voice.errors.TTSError: On any synthesis failure.
        """
