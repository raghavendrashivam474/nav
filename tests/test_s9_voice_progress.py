"""S9 Progressive Voice Interaction tests — deterministic unit tests.

Validates VoiceProgressReporter milestone filtering, error resilience,
and integration with the research progress protocol.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from capabilities.research.progress import ProgressEvent, ProgressStage
from interfaces.voice.audio import AudioOutput
from interfaces.voice.contracts import TextToSpeech
from interfaces.voice.progress import VoiceProgressReporter


class FakeTTS(TextToSpeech):
    @property
    def name(self) -> str:
        return "fake-tts"

    def __init__(self) -> None:
        self.spoken: list[str] = []

    def synthesize(self, text: str) -> AudioOutput:
        self.spoken.append(text)
        return AudioOutput(samples=b"fake-audio", sample_rate=16000)


class FakeSpeaker:
    def __init__(self) -> None:
        self.played: list[AudioOutput] = []

    def play(self, audio: AudioOutput) -> None:
        self.played.append(audio)


class TestVoiceProgressReporter:
    def test_speaks_discovery_milestone(self) -> None:
        tts = FakeTTS()
        speaker = FakeSpeaker()
        reporter = VoiceProgressReporter(tts=tts, speaker=speaker)

        event = ProgressEvent(
            stage=ProgressStage.DISCOVERY,
            message="Discovered 5 sources",
            completed=5,
            total=5,
        )
        reporter.report(event)

        assert len(tts.spoken) == 1
        assert "5 relevant sources" in tts.spoken[0]
        assert len(speaker.played) == 1

    def test_speaks_discovery_milestone_only_once(self) -> None:
        tts = FakeTTS()
        speaker = FakeSpeaker()
        reporter = VoiceProgressReporter(tts=tts, speaker=speaker)

        e1 = ProgressEvent(stage=ProgressStage.DISCOVERY, message="Found 3", total=3)
        e2 = ProgressEvent(stage=ProgressStage.DISCOVERY, message="Found 3", total=3)
        reporter.report(e1)
        reporter.report(e2)

        assert len(tts.spoken) == 1

    def test_ignores_intermediate_retrieval_and_extraction_events(self) -> None:
        tts = FakeTTS()
        speaker = FakeSpeaker()
        reporter = VoiceProgressReporter(tts=tts, speaker=speaker)

        # Emit high-frequency noisy events
        e_ret1 = ProgressEvent(
            stage=ProgressStage.RETRIEVAL,
            message="Retrieved 1/4",
            completed=1,
            total=4,
        )
        e_ret2 = ProgressEvent(
            stage=ProgressStage.RETRIEVAL,
            message="Retrieved 2/4",
            completed=2,
            total=4,
        )
        e_ext1 = ProgressEvent(
            stage=ProgressStage.EXTRACTION,
            message="Extracted 1/4",
            completed=1,
            total=4,
        )

        reporter.report(e_ret1)
        reporter.report(e_ret2)
        reporter.report(e_ext1)

        # Must remain silent during chunks
        assert len(tts.spoken) == 0
        assert len(speaker.played) == 0

    def test_speaks_synthesis_milestone(self) -> None:
        tts = FakeTTS()
        speaker = FakeSpeaker()
        reporter = VoiceProgressReporter(tts=tts, speaker=speaker)

        event = ProgressEvent(stage=ProgressStage.SYNTHESIS, message="Synthesizing")
        reporter.report(event)

        assert len(tts.spoken) == 1
        assert "Synthesizing" in tts.spoken[0]

    def test_disabled_reporter_remains_silent(self) -> None:
        tts = FakeTTS()
        speaker = FakeSpeaker()
        reporter = VoiceProgressReporter(tts=tts, speaker=speaker, enable_spoken_milestones=False)

        reporter.report(ProgressEvent(stage=ProgressStage.DISCOVERY, message="Found 5", total=5))
        assert len(tts.spoken) == 0

    def test_swallows_tts_exceptions_safely(self) -> None:
        failing_tts = MagicMock(spec=TextToSpeech)
        failing_tts.synthesize.side_effect = RuntimeError("Audio device busy")
        speaker = FakeSpeaker()

        reporter = VoiceProgressReporter(tts=failing_tts, speaker=speaker)
        reporter.report(ProgressEvent(stage=ProgressStage.DISCOVERY, message="Found 3", total=3))
