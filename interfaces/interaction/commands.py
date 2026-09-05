"""Deterministic Command Interpreter — S19.

Maps standardized voice/text commands directly to control actions.
Unrecognized input drops back to SEND_MESSAGE (standard conversational flow).
"""

from __future__ import annotations

import re

from interfaces.interaction.contracts import InterpretedCommand, UserAction


class CommandInterpreter:
    """Determines user intent from input text using deterministic matchers."""

    def __init__(self) -> None:
        self._matchers = [
            (
                UserAction.PAUSE,
                r"^\s*(pause|pause that|hold on|hold up|hold|stop working)\b",
            ),
            (
                UserAction.RESUME,
                r"^\s*(resume|continue|keep going|start again|go ahead|resume work)\b",
            ),
            (
                UserAction.CANCEL,
                r"^\s*(cancel|cancel that|stop|stop that|abort|kill|terminate)\b",
            ),
            (
                UserAction.APPROVE,
                r"^\s*(approve|approve that|yes|confirm|proceed|allow|looks good)\b",
            ),
            (
                UserAction.REJECT,
                r"^\s*(reject|reject that|no|deny|disallow|dont do that)\b",
            ),
            (
                UserAction.TAKE_OVER,
                r"^\s*(i'll take over|ill take over|take over|take control|give me control)\b",
            ),
            (
                UserAction.RETURN_CONTROL,
                r"^\s*(return control|give control back|take control back|resume auto|go auto)\b",
            ),
            (
                UserAction.REQUEST_STATUS,
                r"^\s*(status|what is the status|show progress|how is it going|update)\b",
            ),
        ]

    def interpret(self, text: str) -> InterpretedCommand:
        """Parse text to retrieve a target action and relevant variables."""
        cleaned = text.strip().lower()

        # Check for direct command matches first
        for action, pattern in self._matchers:
            if re.match(pattern, cleaned):
                return InterpretedCommand(action=action)

        # Context-dependent patterns with payloads
        # "actually, focus on silicon packaging instead" / "focus on manufacturing feasibility"
        redirect_match = re.match(
            r"^(?:actually[,\s]+)?(?:focus on|do|research|investigate)\s+(.+?)(?:\s+instead)?$",
            cleaned,
        )
        if redirect_match:
            new_obj = redirect_match.group(1).strip()
            # If objective is a command itself (e.g. "stop"), don't treat as redirection
            if new_obj not in ("pause", "resume", "stop", "cancel", "status", "approve", "reject"):
                return InterpretedCommand(
                    action=UserAction.REDIRECT,
                    payload={"new_objective": new_obj, "raw_text": text},
                )

        # Handle explicit input provision
        # "input target is electronics" / "the answer is 42"
        input_match = re.match(r"^(?:input|answer|response is)\s+(.+)$", cleaned)
        if input_match:
            return InterpretedCommand(
                action=UserAction.PROVIDE_INPUT,
                payload={"input_data": {"value": input_match.group(1).strip()}, "raw_text": text},
            )

        # Fallback is conversational request
        return InterpretedCommand(action=UserAction.SEND_MESSAGE, payload={"raw_text": text})
