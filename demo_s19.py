"""NAV S19 Interactive Voice & Presence Model Demo.

Integrates the full S19 stack: Unified Interaction Layer, Presence mappings,
ASCII Presence Renderer, and optional Voice capture adapter.
"""

from __future__ import annotations

import argparse
import time

from capabilities.cognition.cognition import CognitionCapability
from capabilities.work.capability import WorkCapability
from capabilities.work.service import WorkService
from capabilities.work.sqlite_repo import SQLiteWorkRepository
from core.capabilities.registry import CapabilityRegistry
from core.contracts.ai import AIGateway, AIRequest, AIResponse
from core.orchestration.orchestrator import Orchestrator
from interfaces.interaction.contracts import (
    InteractionInput,
    InteractionInputKind,
    NAVInteractionState,
)
from interfaces.interaction.interaction_layer import InteractionLayer
from interfaces.interaction.session import InteractionSession
from interfaces.presence.contracts import PresenceFrame
from interfaces.presence.derivation import interaction_state_to_presence_state
from interfaces.presence.terminal_renderer import TerminalPresenceRenderer


class SmartGateway(AIGateway):
    """Answers intelligently using configured AI providers or contextual responses."""

    def __init__(self) -> None:
        self._real_gateway: AIGateway | None = None
        try:
            from ai.router import ModelRouter  # type: ignore[import-not-found]

            self._real_gateway = ModelRouter()
        except Exception:
            pass

    def generate(self, request: AIRequest) -> AIResponse:
        if self._real_gateway is not None:
            try:
                return self._real_gateway.generate(request)
            except Exception:
                pass

        prompt = request.messages[-1].content.strip()
        lower = prompt.lower().replace("sq lite", "sqlite")

        if "mongodb" in lower and "sqlite" in lower:
            reply = (
                "SQLite is ideal for embedded, serverless, single-file relational storage. "
                "MongoDB is a document store built for high-throughput JSON and scaling."
            )
        elif "who are you" in lower or "about yourself" in lower or "what can you do" in lower:
            reply = (
                "I am NAV, an intelligent technical assistant. I can research technical topics, "
                "orchestrate multi-step execution workflows, and respond to your voice commands."
            )
        elif "hello" in lower or "hi" in lower or "how are you" in lower:
            reply = "Hello! I am operational and ready to assist with research or workflow tasks."
        else:
            reply = (
                f"I understood your request about '{prompt}'. "
                "I can investigate or execute work on this."
            )

        return AIResponse(
            content=reply,
            model_used="smart-gateway",
            usage={},
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="NAV S19 Presence & Interaction Demo")
    parser.add_argument("--voice", action="store_true", help="Enable S19 voice loop adapter")
    args = parser.parse_args()

    print("\nNAV v1.9 - INITIALIZING S19 INTERACTION SURFACE")

    repo = SQLiteWorkRepository(":memory:")
    service = WorkService(repository=repo)
    work_cap = WorkCapability(service)
    cog_cap = CognitionCapability(gateway=SmartGateway())

    registry = CapabilityRegistry()
    registry.register(work_cap)
    registry.register(cog_cap)
    orchestrator = Orchestrator(registry)

    session = InteractionSession()
    layer = InteractionLayer(orchestrator, session)
    renderer = TerminalPresenceRenderer()

    work = service.create_work("Explore silicon packaging")
    service.auto_plan(work.work_id)
    session.focused_work_id = work.work_id

    frame = PresenceFrame(
        state=interaction_state_to_presence_state(layer.get_presence_state()),
        activity_strip=layer._build_activity_strip(),
        focused_work_id=session.focused_work_id,
    )
    renderer.render(frame)

    if args.voice:
        from interfaces.voice.interaction_voice_adapter import InteractionVoiceAdapter
        from interfaces.voice.microphone import Microphone
        from interfaces.voice.speaker import Speaker
        from interfaces.voice.stt.factory import create_stt
        from interfaces.voice.tts.factory import create_tts

        print("\n[OK] Voice Loop Enabled. Ready to capture.")
        print("Commands: Speak 'pause', 'resume', 'status', or ask. Type 'exit' to quit.\n")
        mic = Microphone()
        speaker = Speaker()
        stt = create_stt()
        tts = create_tts()
        adapter = InteractionVoiceAdapter(layer, mic, stt, tts, speaker)

        while True:
            try:
                print("[Press Enter to speak 5 seconds of audio, or type 'exit' to quit]")
                cmd = input("You (voice-toggle) > ").strip().lower()
                if cmd == "exit":
                    break

                print("\n>>> [Listening... Speak now into your microphone] <<<")
                out = adapter.run_voice_cycle(max_seconds=5.0)

                if out is not None:
                    print(f'\nYou said: "{adapter.last_transcript}"')
                    p_state = interaction_state_to_presence_state(layer.get_presence_state())
                    frame = PresenceFrame(
                        state=p_state,
                        activity_strip=out.activity_strip,
                        current_utterance=out.utterance,
                        focused_work_id=session.focused_work_id,
                    )
                    renderer.render(frame)

                    if out.interaction_state == NAVInteractionState.WORKING:
                        print("  [Simulating 1.0s automated background work execution step...]")
                        time.sleep(1.0)
                        service.execute_next_step(session.focused_work_id)
                        frame = PresenceFrame(
                            state=interaction_state_to_presence_state(layer.get_presence_state()),
                            activity_strip=layer._build_activity_strip(),
                            focused_work_id=session.focused_work_id,
                        )
                        renderer.render(frame)
                else:
                    print("\n[No speech detected or recording was silent. Try speaking louder.]")

            except KeyboardInterrupt:
                break
    else:
        print("\n[OK] Running in Text Mode REPL.")
        print("Commands: 'Research semiconductors', 'pause', 'resume', 'cancel', 'exit'\n")

        while True:
            try:
                user_text = input("You > ").strip()
                if not user_text or user_text.lower() in ("exit", "quit"):
                    break

                user_input = InteractionInput(text=user_text, kind=InteractionInputKind.TEXT)
                out = layer.process_input(user_input)

                p_state = interaction_state_to_presence_state(layer.get_presence_state())
                frame = PresenceFrame(
                    state=p_state,
                    activity_strip=out.activity_strip,
                    current_utterance=out.utterance,
                    focused_work_id=session.focused_work_id,
                )
                renderer.render(frame)

                if out.interaction_state == NAVInteractionState.WORKING:
                    print("  [Simulating 1.0s automated background work execution step...]")
                    time.sleep(1.0)
                    service.execute_next_step(session.focused_work_id)
                    frame = PresenceFrame(
                        state=interaction_state_to_presence_state(layer.get_presence_state()),
                        activity_strip=layer._build_activity_strip(),
                        focused_work_id=session.focused_work_id,
                    )
                    renderer.render(frame)

            except KeyboardInterrupt:
                break


if __name__ == "__main__":
    main()
