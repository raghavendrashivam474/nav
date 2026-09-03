"""NAV voice error hierarchy.

Mirrors the ai/errors.py pattern from S3: provider-specific exceptions
never leak into Core. Everything a voice component raises is a subclass
of VoiceError so callers can handle voice failures uniformly.
"""

from __future__ import annotations


class VoiceError(Exception):
    """Base class for all NAV voice-layer errors."""


class ConfigurationError(VoiceError):
    """Raised when the voice layer is misconfigured (env vars, missing deps)."""


class MicrophoneError(VoiceError):
    """Raised when microphone capture fails or produces no audio."""


class STTError(VoiceError):
    """Raised when speech-to-text transcription fails."""


class TTSError(VoiceError):
    """Raised when text-to-speech synthesis fails."""


class PlaybackError(VoiceError):
    """Raised when audio playback fails."""
