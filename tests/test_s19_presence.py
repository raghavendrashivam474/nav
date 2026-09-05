import io
import unittest

from interfaces.interaction.contracts import InteractionActivity, NAVInteractionState
from interfaces.presence.contracts import PresenceFrame, PresenceState
from interfaces.presence.derivation import interaction_state_to_presence_state
from interfaces.presence.terminal_renderer import TerminalPresenceRenderer


class TestPresenceModel(unittest.TestCase):
    def test_state_derivation(self) -> None:
        self.assertEqual(
            interaction_state_to_presence_state(NAVInteractionState.WORKING),
            PresenceState.WORKING,
        )
        self.assertEqual(
            interaction_state_to_presence_state(NAVInteractionState.PAUSED),
            PresenceState.PAUSED,
        )

    def test_terminal_renderer_isolated_output(self) -> None:
        stream = io.StringIO()
        renderer = TerminalPresenceRenderer(output_stream=stream)

        frame = PresenceFrame(
            state=PresenceState.WORKING,
            activity_strip=(
                InteractionActivity(
                    description="Searching relevant documentation",
                    timestamp="2026-09-06T12:00:00Z",
                    activity_type="step_started",
                ),
            ),
            current_utterance="Analyzing semiconductor packages...",
        )

        renderer.render(frame)
        output = stream.getvalue()

        self.assertIn("NAV Presence: WORKING", output)
        self.assertIn("Analyzing semiconductor packages...", output)
        self.assertIn("Searching relevant documentation", output)
