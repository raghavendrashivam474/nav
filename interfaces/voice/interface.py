"""VoiceInterface ? the S4 press-to-talk orchestration boundary.

Voice is a *communication modality*, not a reasoning capability. This class
turns audio into a normal NAV Request, hands it to the Orchestrator, and
speaks whatever comes back. It does not think, remember, or route on its
own. If tomorrow we delete this module, NAV Core still works.

Golden invariant:

    A voice-originated request is *indistinguishable* from a text-originated
    request once it reaches the Orchestrator.
"""

from __future__ import annotations

import uuid

from core.contracts.capability import Request, Response
from core.log import get_logger
from core.orchestration.orchestrator import Orchestrator
from interfaces.voice.contracts import SpeechToText, TextToSpeech
from interfaces.voice.errors import MicrophoneError, STTError, TTSError, VoiceError
from interfaces.voice.microphone import MicrophoneProtocol
from interfaces.voice.speaker import SpeakerProtocol

logger = get_logger(__name__)


class VoiceInterface:
    """One press-to-talk voice cycle wired to the existing NAV pipeline."""

    def __init__(
        self,
        orchestrator: Orchestrator,
        microphone: MicrophoneProtocol,
        stt: SpeechToText,
        tts: TextToSpeech,
        speaker: SpeakerProtocol,
        capability: str = "cognition",
    ) -> None:
        self._orchestrator = orchestrator
        self._microphone = microphone
        self._stt = stt
        self._tts = tts
        self._speaker = speaker
        self._capability = capability

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_once(self, max_seconds: float = 8.0) -> Response:
        """Execute one full press-to-talk cycle.

        Steps:
            1. Capture audio from the microphone.
            2. Transcribe it via the injected STT provider.
            3. Build a normal NAV Request and route it through the Orchestrator.
            4. Synthesize the reply via the injected TTS provider.
            5. Play the audio (unless TTS already self-played).

        Any voice-layer failure is translated into a failed ``Response`` so
        callers never see a bare exception.
        """
        request_id = f"voice_{uuid.uuid4().hex[:8]}"
        logger.info("Voice session started (id=%s)", request_id)

        # 1. Capture ---------------------------------------------------
        try:
            logger.info("Recording (max_seconds=%.1f)...", max_seconds)
            audio = self._microphone.record(max_seconds)
        except MicrophoneError as exc:
            return self._fail(request_id, f"Microphone error: {exc}")

        # 2. Transcribe ------------------------------------------------
        try:
            logger.info("Transcribing via %s...", self._stt.name)
            transcript = self._stt.transcribe(audio).strip()
        except STTError as exc:
            return self._fail(request_id, f"Transcription error: {exc}")

        if not transcript:
            return self._fail(request_id, "No speech detected in audio.")

        logger.info("Transcript: %r", transcript)

        # 3. Route through NAV ----------------------------------------
        nav_request = Request(request_id=request_id, payload={"prompt": transcript})
        response = self._orchestrator.route_request(self._capability, nav_request)

        if not response.success:
            logger.warning("Cognition failed: %s", response.error)
            self._try_speak(f"Sorry, something went wrong. {response.error or ''}".strip())
            return response

        reply = str(response.data.get("reply", "")).strip()
        if not reply:
            return self._fail(request_id, "Cognition returned an empty reply.")

        # 4 + 5. Synthesize + Play ------------------------------------
        try:
            self._speak(reply)
        except VoiceError as exc:
            logger.error("Voice output failed: %s", exc)
            # Preserve the successful cognition response even if playback fails.
            return Response(
                request_id=response.request_id,
                data=response.data,
                success=False,
                error=f"Voice output error: {exc}",
            )

        logger.info("Voice session complete (id=%s)", request_id)
        return response

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _speak(self, text: str) -> None:
        logger.info("Synthesizing via %s (%d chars)", self._tts.name, len(text))
        audio_out = self._tts.synthesize(text)
        if audio_out.metadata.get("self_played"):
            logger.info("TTS provider handled playback directly.")
            return
        self._speaker.play(audio_out)

    def _try_speak(self, text: str) -> None:
        """Best-effort spoken error message. Never raises."""
        try:
            self._speak(text)
        except VoiceError as exc:
            logger.error("Failed to speak error message: %s", exc)
        except Exception as exc:
            logger.error("Unexpected error while speaking error message: %s", exc)

    @staticmethod
    def _fail(request_id: str, message: str) -> Response:
        logger.error("Voice session failed (id=%s): %s", request_id, message)
        return Response(request_id=request_id, data={}, success=False, error=message)


__all__ = ["VoiceInterface", "TTSError"]
