"""STT provider factory. Selects implementation via NAV_STT_PROVIDER."""

from __future__ import annotations

import os

from core.log import get_logger
from interfaces.voice.contracts import SpeechToText
from interfaces.voice.errors import ConfigurationError

logger = get_logger(__name__)


def create_stt() -> SpeechToText:
    """Instantiate the STT provider selected by the environment.

    Supported values of ``NAV_STT_PROVIDER``:
        * ``whisper`` (default) ? local faster-whisper
        * ``mock`` ? deterministic in-memory stub
    """
    provider = os.environ.get("NAV_STT_PROVIDER", "whisper").lower()
    logger.info("Creating STT provider: %s", provider)

    if provider == "whisper":
        from interfaces.voice.stt.whisper_stt import WhisperSTT

        return WhisperSTT()

    if provider == "mock":
        from interfaces.voice.stt.mock_stt import MockSTT

        return MockSTT()

    raise ConfigurationError(f"Unsupported STT provider: '{provider}'")
