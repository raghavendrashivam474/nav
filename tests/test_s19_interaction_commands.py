import unittest

from interfaces.interaction.commands import CommandInterpreter
from interfaces.interaction.contracts import UserAction


class TestCommandInterpreter(unittest.TestCase):
    def setUp(self) -> None:
        self.interpreter = CommandInterpreter()

    def test_deterministic_control_commands(self) -> None:
        cases = [
            ("pause", UserAction.PAUSE),
            ("Pause That", UserAction.PAUSE),
            ("hold on", UserAction.PAUSE),
            ("resume", UserAction.RESUME),
            ("continue", UserAction.RESUME),
            ("keep going", UserAction.RESUME),
            ("cancel", UserAction.CANCEL),
            ("stop that", UserAction.CANCEL),
            ("approve", UserAction.APPROVE),
            ("yes", UserAction.APPROVE),
            ("reject", UserAction.REJECT),
            ("no", UserAction.REJECT),
            ("take over", UserAction.TAKE_OVER),
            ("return control", UserAction.RETURN_CONTROL),
            ("status", UserAction.REQUEST_STATUS),
            ("show progress", UserAction.REQUEST_STATUS),
        ]

        for text, expected_action in cases:
            interpreted = self.interpreter.interpret(text)
            self.assertEqual(interpreted.action, expected_action, f"Failed on: {text}")

    def test_redirect_command(self) -> None:
        interpreted = self.interpreter.interpret("Actually, focus on silicon packaging instead")
        self.assertEqual(interpreted.action, UserAction.REDIRECT)
        self.assertEqual(interpreted.payload.get("new_objective"), "silicon packaging")

    def test_conversational_fallback(self) -> None:
        prompt = "What are the primary challenges of semiconductor design?"
        interpreted = self.interpreter.interpret(prompt)
        self.assertEqual(interpreted.action, UserAction.SEND_MESSAGE)
        self.assertEqual(interpreted.payload.get("raw_text"), prompt)
