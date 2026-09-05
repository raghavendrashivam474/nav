# ADR 0008 — S19 Interaction Boundary and Presence Model

**Status:** Accepted
**Date:** S19
**Supersedes:** none
**Superseded by:** none
**Related:** ADR 0001 (voice remains interface), ADR 0002 (runtime
boundary), ADR 0006-s18 (human control).

## Context

Through S18, NAV has a complete backend capable of context, memory,
research, bounded work execution, and human-in-the-loop control. All 17
Work control actions are exposed on `WorkCapability` and routed through
`Orchestrator`. There is no user-facing interaction layer that turns
those capabilities into a natural conversation with visible presence.

S19 must introduce that layer without regressing any S17/S18 semantics
(§23, §38 of the S19 sprint spec).

Two facts constrain design:

1. **There is no "active work" concept in the backend.** `WorkStatus`
   tracks lifecycle; nothing tracks user focus.
2. **`WorkCapability.status` returns only counts of activity**, not the
   activity entries themselves. The interaction layer needs the last
   1–2 meaningful activity entries to render the activity strip.

## Decision

### D1. Introduce two new peer packages under `interfaces/`

- `interfaces/interaction/` — interaction contract, command interpreter,
  session focus, state and activity mappings, `WorkControlAdapter`, and
  the `InteractionLayer` boundary.
- `interfaces/presence/` — `PresenceState`, `PresenceRenderer` protocol,
  and a first `TerminalPresenceRenderer`.

Both packages live at the same layer as `interfaces/voice/`. Neither
imports from `capabilities/*` internals; they interact with the backend
exclusively through `Orchestrator.route_request(capability_name, Request)`.

### D2. Active-work focus lives in the interaction layer only

`InteractionSession.focused_work_id` is an in-memory pointer scoped to
one interaction session. The backend gains no new field, no new state,
no new state machine. This is not a Work state — it is a UI focus
pointer, analogous to a text editor's "current buffer".

**Rejected alternative:** adding an `active`/`focused` flag on `Work`.
That would introduce a second lifecycle concept (focus) into the Work
state machine, breaking §23 ("no second Work state machine").

### D3. `VoiceInterface` is not modified

S19 introduces `InteractionVoiceAdapter` as a peer. Existing S4/S9/S10
consumers of `VoiceInterface` continue to work unchanged. The two paths
coexist:

    S4/S9/S10 legacy:  Mic -> STT -> VoiceInterface     -> Orchestrator("cognition")
    S19:               Mic -> STT -> InteractionLayer    -> Orchestrator("cognition"|"work"|...)
                                        (via InteractionVoiceAdapter)

`demo_s19.py` uses the S19 path; existing tests using `VoiceInterface`
continue as-is.

**Rejected alternative:** rewriting `VoiceInterface` to route through
the interaction layer. That would risk regressions in S4/S9/S10 tests
and violates §38's "am I redesigning something S17/S18 already solved?"
check for the voice-orchestrator seam that predates S19.

### D4. Interaction state and presence state are derived, not stored

The dependency arrow is:

    WorkStatus (backend)
      -> NAVInteractionState (derived by `state_mapping.py`)
        -> PresenceState (derived by `presence/derivation.py`)
          -> Renderer output

Renderers never own state. `TerminalPresenceRenderer.render(frame)`
takes an immutable `PresenceFrame` and emits output. A future
graphical renderer replaces `TerminalPresenceRenderer` with no impact
on interaction or backend code (§14).

### D5. One additive, backward-compatible touch to WorkCapability

`_handle_status(request)` gains optional payload fields:

- `include_activity: bool = False`
- `activity_limit: int = 2`

When `include_activity` is absent or falsy, the response payload is
byte-identical to the S18 payload:

    { work_id, objective, status, completed_steps, pending_steps, activity_count }

When `include_activity` is truthy, the response payload additionally
contains:

    "recent_activity": [
        {
            "timestamp": ...,
            "activity_type": ...,
            "description": ...,
            "step_id": ... or None,
            "metadata": {...}
        },
        ...
    ]

Entries are the most recent `activity_limit` items from
`Work.activity_log`, in reverse-chronological order (newest first).
The `WorkService`, `WorkRepository`, `Work`, `WorkActivity`, and every
enum remain untouched.

**Rejected alternative A:** a new `activity` action. Adds a new
action string that duplicates 90% of what `status` already returns.

**Rejected alternative B:** reading `Work.activity_log` from the
interaction layer via a new `WorkService` method. Widens the service
surface and creates a direct interaction → service call path,
bypassing the capability boundary. Rejected.

### D6. First renderer is terminal-only, stdlib only

The renderer decision is deliberately deferred (§27). The first
concrete renderer uses only `sys.stdout` so S19 adds no new direct
dependency and can prove the interaction/presence separation without
committing to a graphics stack. Any future renderer implements the
`PresenceRenderer` protocol and drops in without changing interaction
semantics.

## Consequences

### Positive
- Zero risk to S17/S18 behaviour.
- Interaction layer testable end-to-end in pure text mode with no
  audio hardware, no network, no graphics.
- Presence renderer swappable at any future sprint.
- Clean seam for S20 (security) to insert authorization between
  interaction control actions and capability dispatch.

### Negative
- Two voice paths exist temporarily (`VoiceInterface` and the new
  `InteractionVoiceAdapter`). A future sprint may consolidate.
- The interaction layer keeps a small in-memory focus pointer; if the
  process restarts, the user must re-reference the target work
  explicitly. Persistent focus, if ever needed, becomes an interaction-
  layer concern, still not a backend concern.

### Neutral
- The additive `include_activity` field is a low-risk, well-scoped
  extension. No ADR is required for extending it further in future
  sprints as long as the flag-absent payload remains byte-identical.

## Compatibility

- S17/S18 tests: unchanged, all green.
- S4/S9/S10 voice tests: unchanged, all green.
- Existing `WorkCapability` callers: identical response payloads when
  `include_activity` is not passed.
- No frozen contract changed.
