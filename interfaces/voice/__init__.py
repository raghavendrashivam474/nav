"""NAV voice interface (S4 + S9).

Public surface:
    VoiceInterface      — the press-to-talk orchestration boundary
    VoiceProgressReporter — natural, selective milestone reporting for long operations
    AudioInput/Output   — provider-neutral audio value objects
    SpeechToText        — STT contract
    TextToSpeech        — TTS contract
    Microphone/Speaker  — real hardware implementations (require voice extras)
    FakeMicrophone/FakeSpeaker — test doubles

Provider factories:
    interfaces.voice.stt.factory.create_stt()
    interfaces.voice.tts.factory.create_tts()
"""

from interfaces.voice.audio import AudioInput, AudioOutput
from interfaces.voice.contracts import SpeechToText, TextToSpeech
from interfaces.voice.errors import (
    ConfigurationError,
    MicrophoneError,
    PlaybackError,
    STTError,
    TTSError,
    VoiceError,
)
from interfaces.voice.interface import VoiceInterface
from interfaces.voice.microphone import FakeMicrophone, Microphone
from interfaces.voice.progress import VoiceProgressReporter
from interfaces.voice.speaker import FakeSpeaker, Speaker

__all__ = [
    "AudioInput",
    "AudioOutput",
    "ConfigurationError",
    "FakeMicrophone",
    "FakeSpeaker",
    "Microphone",
    "MicrophoneError",
    "PlaybackError",
    "Speaker",
    "SpeechToText",
    "STTError",
    "TextToSpeech",
    "TTSError",
    "VoiceError",
    "VoiceInterface",
    "VoiceProgressReporter",
]
