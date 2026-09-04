"""VoiceInterface — the S4 press-to-talk orchestration boundary.

S10: Added session continuity tracking so multi-turn voice
conversations preserve research context across turns.

Golden invariant:
    A voice-originated request is indistinguishable from a text-originated
    request once it reaches the Orchestrator.
"""

from __future__ import annotations

import uuid

from core.contracts.capability import Request, Response
from core.log import get_logger
from core.orchestration.orchestrator import Orchestrator
from interfaces.voice.contracts import SpeechToText, TextToSpeech
from interfaces.voice.errors import MicrophoneError, STTError, TTSError
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
        self._active_session_id: str | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_once(self, max_seconds: float = 8.0) -> Response:
        request_id = f"voice_{uuid.uuid4().hex[:8]}"
        logger.info("Voice session started (id=%s)", request_id)

        # 1. Capture
        try:
            logger.info("Recording (max_seconds=%.1f)...", max_seconds)
            audio = self._microphone.record(max_seconds)
        except MicrophoneError as exc:
            return self._fail(request_id, f"Microphone error: {exc}")

        # 2. Transcribe
        try:
            logger.info("Transcribing via %s...", self._stt.name)
            transcript = self._stt.transcribe(audio).strip()
        except STTError as exc:
            return self._fail(request_id, f"Transcription error: {exc}")

        if not transcript:
            return self._fail(request_id, "No speech detected in audio.")

        logger.info("Transcript: %r", transcript)

        # 3. Route through NAV
        payload: dict[str, object] = {"prompt": transcript}
        if self._active_session_id:
            payload["session_id"] = self._active_session_id

        nav_request = Request(request_id=request_id, payload=payload)
        response = self._orchestrator.route_request(self._capability, nav_request)

        if not response.success:
            logger.warning("Cognition failed: %s", response.error)
            self._try_speak(f"Sorry, something went wrong. {response.error or ''}".strip())
            return response

        # S10: Track session from response
        new_session = response.data.get("session_id")
        if new_session:
            self._active_session_id = str(new_session)

        reply = str(response.data.get("reply", "")).strip()
        if not reply:
            return self._fail(request_id, "Cognition returned an empty reply.")

        # 4 + 5. Synthesize + Play
        try:
            logger.info("Synthesizing reply via %s...", self._tts.name)
            audio_out = self._tts.synthesize(reply)
        except TTSError as exc:
            logger.warning("TTS failed: %s", exc)
            return self._fail(request_id, f"Voice output error: {exc}")

        try:
            self._speaker.play(audio_out)
        except Exception as exc:
            logger.warning("Speaker playback failed (non-fatal): %s", exc)

        return response

    def reset_session(self) -> None:
        """Clear the active research session (S10)."""
        self._active_session_id = None
        logger.info("Voice session context reset")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _try_speak(self, text: str) -> None:
        try:
            audio = self._tts.synthesize(text)
            self._speaker.play(audio)
        except Exception:
            pass

    @staticmethod
    def _fail(request_id: str, error: str) -> Response:
        logger.warning("Voice cycle failed: %s", error)
        return Response(request_id=request_id, data={}, success=False, error=error)
