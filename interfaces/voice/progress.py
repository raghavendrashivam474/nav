"""Progressive voice reporting for long-running operations — S9.

Implements the ProgressReporter protocol from capabilities.research.progress
to provide selective, natural spoken milestones during research operations.

Adheres to Brief §14:
  - Does NOT speak high-frequency noise (e.g., each source retrieval).
  - Speaks concise, informative milestone updates:
      * DISCOVERY milestone: "I found 5 relevant sources. I'm analyzing them now."
      * SYNTHESIS milestone: "Synthesizing the evidence now."
  - Swallows any TTS playback exceptions so research progress is never blocked.
"""

from __future__ import annotations

from capabilities.research.progress import ProgressEvent, ProgressStage
from core.log import get_logger
from interfaces.voice.contracts import TextToSpeech
from interfaces.voice.speaker import SpeakerProtocol

logger = get_logger(__name__)


class VoiceProgressReporter:
    """Consumes ProgressEvents and speaks selected high-value milestones."""

    def __init__(
        self,
        tts: TextToSpeech,
        speaker: SpeakerProtocol,
        enable_spoken_milestones: bool = True,
    ) -> None:
        self._tts = tts
        self._speaker = speaker
        self._enabled = enable_spoken_milestones
        self._spoken_milestones: set[ProgressStage] = set()

    def report(self, event: ProgressEvent) -> None:
        """Process a progress event and speak if it represents a major milestone."""
        if not self._enabled:
            return

        milestone_text = self._format_milestone(event)
        if milestone_text is not None:
            self._speak_safely(milestone_text)

    def _format_milestone(self, event: ProgressEvent) -> str | None:
        """Convert selected progress stages into natural, non-repetitive voice prompts."""
        # Speak DISCOVERY milestone once when sources are found
        is_disc = event.stage == ProgressStage.DISCOVERY
        if is_disc and ProgressStage.DISCOVERY not in self._spoken_milestones:
            self._spoken_milestones.add(ProgressStage.DISCOVERY)
            if event.total > 0:
                return f"I found {event.total} relevant sources. Analyzing them now."
            return "Searching for relevant sources."

        # Speak SYNTHESIS milestone once
        is_synth = event.stage == ProgressStage.SYNTHESIS
        if is_synth and ProgressStage.SYNTHESIS not in self._spoken_milestones:
            self._spoken_milestones.add(ProgressStage.SYNTHESIS)
            return "Synthesizing the evidence now."

        # Other stages (STARTED, RETRIEVAL chunks, EXTRACTION chunks, COMPLETED) remain silent
        return None

    def _speak_safely(self, text: str) -> None:
        """Speak a milestone message, swallowing errors to prevent operation failure."""
        try:
            logger.info("Voice progress milestone: %r", text)
            audio_out = self._tts.synthesize(text)
            if not audio_out.metadata.get("self_played"):
                self._speaker.play(audio_out)
        except Exception as exc:
            logger.warning("Voice progress announcement failed (non-fatal): %s", exc)

    def reset(self) -> None:
        """Reset spoken milestones for a new session."""
        self._spoken_milestones.clear()
