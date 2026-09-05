"""Terminal Presence Renderer — S19.

A purely synthetic, non-photorealistic ASCII terminal presence renderer.
Builds recognizable shapes communicating state, isolated from core mechanics.
"""

from __future__ import annotations

import sys

from interfaces.presence.contracts import PresenceFrame, PresenceState


class TerminalPresenceRenderer:
    """Renders state-driven ASCII visual frames to stdout."""

    def __init__(self, output_stream=None) -> None:
        self._out = output_stream or sys.stdout

    def render(self, frame: PresenceFrame) -> None:
        """Express visual presence representation."""
        # Visual assets matching spec state-behavior concepts
        ascii_states = {
            PresenceState.IDLE: """
               . . . . .
              .         .
              .   (o)   .
              .         .
               . . . . .
            """,
            PresenceState.LISTENING: """
               * * * * *
              *  ( . )  *
              * ( . . ) *
              *  ( . )  *
               * * * * *
            """,
            PresenceState.THINKING: """
               ? ? ? ? ?
              ?  *   *  ?
              ?    *    ?
              ?  *   *  ?
               ? ? ? ? ?
            """,
            PresenceState.WORKING: """
               # # # # #
              # o . * o #
              # * o . * #
              # . * o . #
               # # # # #
            """,
            PresenceState.WAITING_FOR_APPROVAL: """
               ! ! ! ! !
              !  [ ? ]  !
              !  - - -  !
              !  [ ? ]  !
               ! ! ! ! !
            """,
            PresenceState.WAITING_FOR_INPUT: """
               > > > > >
              >  [ _ ]  >
              >  =====  >
              >  [ _ ]  >
               > > > > >
            """,
            PresenceState.PAUSED: """
               | | | | |
              |  [ ] [ ]  |
              |  [ ] [ ]  |
              |  [ ] [ ]  |
               | | | | |
            """,
            PresenceState.RESPONDING: """
               ( ( ( ( (
              (   (o)   )
              (  / | \\  )
              (         )
               ) ) ) ) )
            """,
            PresenceState.COMPLETED: """
               @ @ @ @ @
              @  \\ | /  @
              @  - o -  @
              @  / | \\  @
               @ @ @ @ @
            """,
            PresenceState.ERROR: """
               X X X X X
              X  \\   /  X
              X    X    X
              X  /   \\  X
               X X X X X
            """,
        }

        art = ascii_states.get(frame.state, "   ● ● ● ●   ")

        # Compile visual block
        output = []
        output.append("\n" + "=" * 50)
        output.append(f" NAV Presence: {frame.state.upper()}")
        output.append("=" * 50)
        output.append(art.strip())

        # Display conversational response
        if frame.current_utterance:
            output.append("\n  NAV says:")
            output.append(f'  "{frame.current_utterance}"')

        # Display activity strip
        output.append("\n  [Activity Strip]")
        if frame.activity_strip:
            for act in frame.activity_strip[:2]:
                output.append(f"  → {act.description}")
        else:
            output.append("  → Static Idle")
        output.append("=" * 50 + "\n")

        # Write to stream
        self._out.write("\n".join(output) + "\n")
        self._out.flush()
