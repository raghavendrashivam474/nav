"""Provider-neutral audio value objects.

These exist solely to prevent STT/TTS implementations from leaking their
native audio types (numpy arrays, torch tensors, raw WAV bytes, file paths)
into the rest of NAV. Every voice provider adapts to and from these types.

Kept intentionally minimal ? this is not an audio framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AudioInput:
    """A captured audio buffer destined for speech-to-text.

    Attributes:
        samples: Raw PCM samples. Type is provider-neutral (bytes, list,
            numpy array, etc.) ? providers know how to interpret their own
            expected format. Kept as ``Any`` deliberately to avoid pinning
            NAV to a specific audio library.
        sample_rate: Samples per second (e.g. 16000).
        channels: Number of audio channels (1 = mono).
        duration_seconds: Length of the recording. Optional but useful for logs.
    """

    samples: Any
    sample_rate: int
    channels: int = 1
    duration_seconds: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AudioOutput:
    """A synthesized audio buffer ready for playback.

    Attributes:
        samples: Raw PCM samples or an equivalent playable payload. Type is
            deliberately ``Any`` ? the Speaker knows how to play what the
            paired TTS provider produced.
        sample_rate: Samples per second.
        channels: Number of audio channels.
    """

    samples: Any
    sample_rate: int
    channels: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)
