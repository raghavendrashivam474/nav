"""TTS provider factory. Selects implementation via NAV_TTS_PROVIDER."""

from __future__ import annotations

import os

from core.log import get_logger
from interfaces.voice.contracts import TextToSpeech
from interfaces.voice.errors import ConfigurationError

logger = get_logger(__name__)


def create_tts() -> TextToSpeech:
    """Instantiate the TTS provider selected by the environment.

    Supported values of ``NAV_TTS_PROVIDER``:
        * ``pyttsx3`` (default) ? offline OS-native TTS
        * ``mock`` ? deterministic in-memory stub
    """
    provider = os.environ.get("NAV_TTS_PROVIDER", "pyttsx3").lower()
    logger.info("Creating TTS provider: %s", provider)

    if provider == "pyttsx3":
        from interfaces.voice.tts.pyttsx3_tts import Pyttsx3TTS

        return Pyttsx3TTS()

    if provider == "mock":
        from interfaces.voice.tts.mock_tts import MockTTS

        return MockTTS()

    raise ConfigurationError(f"Unsupported TTS provider: '{provider}'")
