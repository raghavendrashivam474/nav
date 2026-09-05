"""Interaction Voice Adapter — S19.

Adapts raw Audio I/O streams directly to and from S19 Interaction boundaries.
Provides standard voice support without breaking legacy S4 VoiceInterface pathways.
"""

from __future__ import annotations

import uuid

from core.log import get_logger
from interfaces.interaction.contracts import InteractionInput, InteractionInputKind
from interfaces.interaction.interaction_layer import InteractionLayer
from interfaces.voice.contracts import SpeechToText, TextToSpeech
from interfaces.voice.errors import MicrophoneError, STTError
from interfaces.voice.microphone import MicrophoneProtocol
from interfaces.voice.speaker import SpeakerProtocol

logger = get_logger(__name__)


class InteractionVoiceAdapter:
    """Voice adapter orchestrating STT/TTS inputs over unified InteractionLayers."""

    def __init__(
        self,
        interaction_layer: InteractionLayer,
        microphone: MicrophoneProtocol,
        stt: SpeechToText,
        tts: TextToSpeech,
        speaker: SpeakerProtocol,
    ) -> None:
        self._layer = interaction_layer
        self._microphone = microphone
        self._stt = stt
        self._tts = tts
        self._speaker = speaker

    def run_voice_cycle(self, max_seconds: float = 8.0) -> bool:
        """Run a single capture-transcribe-process-synthesize cycle.

        Returns True on transcript processed, False on no voice / hardware error.
        """
        req_id = f"voice_cycle_{uuid.uuid4().hex[:8]}"
        logger.info("Starting voice interaction loop (%s)", req_id)

        # Update transient visual state
        self._layer.session.is_listening = True

        try:
            logger.info("Recording microphone buffer...")
            audio_in = self._microphone.record(max_seconds)
        except MicrophoneError as exc:
            logger.warning("Microphone capture failed: %s", exc)
            self._layer.session.is_listening = False
            return False

        # Transition transient visuals
        self._layer.session.is_listening = False
        self._layer.session.is_thinking = True

        try:
            logger.info("Transcribing audio...")
            transcript = self._stt.transcribe(audio_in).strip()
        except STTError as exc:
            logger.warning("STT transcription failed: %s", exc)
            self._layer.session.is_thinking = False
            return False

        if not transcript:
            logger.info("Empty audio transcription buffer.")
            self._layer.session.is_thinking = False
            return False

        logger.info("Transcript detected: %r", transcript)

        # Dispatch straight through S19 interaction boundary
        user_input = InteractionInput(text=transcript, kind=InteractionInputKind.VOICE)
        output = self._layer.process_input(user_input)

        # Synthesis response handling
        self._layer.session.is_speaking = True
        try:
            logger.info("Synthesizing response utterance...")
            audio_out = self._tts.synthesize(output.utterance)
            self._speaker.play(audio_out)
        except Exception as exc:
            logger.warning("Speech output generation failed: %s", exc)
        finally:
            self._layer.session.is_speaking = False

        return True
