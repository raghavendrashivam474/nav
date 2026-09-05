# S19 Implementation Plan

**Sprint:** S19 — Interaction & Presence Model
**Baseline:** v1.8 (`72a8dfd`)
**Branch:** `sprint/s19-interaction-presence`

This plan is grounded in `S19-recon-notes.md`. It replaces the generic
phasing in the sprint spec §26 only where recon revealed a specific
ordering constraint. All spec §34 Definition-of-Done checkboxes remain
mandatory.

## Guiding principles

1. **Add, do not rewrite.** Every S19 module lives in new packages
   (`interfaces/interaction/`, `interfaces/presence/`). The single
   controlled touch to `capabilities/work/capability.py` is additive and
   backward-compatible.
2. **Correctness before UI.** The interaction contract, command
   interpreter, control adapter, and mappings are all built and tested
   in pure text mode. Voice and rendering come last.
3. **Backend is source of truth.** Interaction state is *derived* from
   backend `WorkStatus`; presence is *derived* from interaction state.
   The dependency arrow never reverses.
4. **No new direct dependency.** First renderer is stdlib-only terminal
   output.

## Phase order

### Phase 0 — Documentation of intent (this doc + ADR)
- `docs/s19/S19-recon-notes.md` — DONE
- `docs/s19/baseline.md` — DONE
- `docs/s19/S19-plan.md` — DONE (this file)
- `docs/architecture/decisions/0008-s19-interaction-boundary.md`

### Phase 1 — Additive backend touch
- Extend `WorkCapability._handle_status` with `include_activity` and
  `activity_limit`. Preserve legacy payload exactly when flag is falsy.
- Test `tests/test_s19_status_activity.py` proves both:
  - legacy payload unchanged when `include_activity` absent,
  - new payload contains the latest N structured activity entries in
    reverse-chronological order when `include_activity=True`.
- **Do not** run S17/S18 tests through this new field. They remain
  passive proofs that the legacy path is intact.

### Phase 2 — Interaction contracts (pure data)
- `interfaces/interaction/contracts.py`
  - `InteractionInputKind` (VOICE, TEXT)
  - `InteractionInput`
  - `InteractionOutputKind` (SPEAK, CONTROL_ACK, ERROR, IDLE)
  - `InteractionOutput`
  - `NAVInteractionState` enum
  - `InteractionActivity`
  - `UserAction` enum (SEND_MESSAGE, PAUSE, RESUME, CANCEL, REDIRECT,
    APPROVE, REJECT, PROVIDE_INPUT, TAKE_OVER, RETURN_CONTROL,
    REQUEST_STATUS)
  - `InterpretedCommand`

### Phase 3 — Interaction session + command interpreter
- `interfaces/interaction/session.py` — `InteractionSession` holding
  `focused_work_id`, `is_listening`, `is_thinking`, `is_speaking`.
- `interfaces/interaction/commands.py` — deterministic mapping of
  common voice/text phrases to `InterpretedCommand`. Ambiguous or
  novel input becomes `SEND_MESSAGE` (falls through to cognition).

### Phase 4 — State + activity mapping
- `interfaces/interaction/state_mapping.py` — pure function
  `work_status_to_interaction_state(WorkStatus) -> NAVInteractionState`
  per spec §5.
- `interfaces/interaction/activity_mapping.py` — pure function
  `work_activity_to_interaction_activity(WorkActivity) ->
  InteractionActivity | None`. Drops chain-of-thought-adjacent types;
  returns human-readable descriptions.

### Phase 5 — Work control adapter
- `interfaces/interaction/work_control.py` — `WorkControlAdapter` that
  takes an `Orchestrator` and translates each `UserAction` into a
  `Request(payload={"action": ..., "work_id": ...})` and dispatches via
  `route_request("work", request)`. Returns `Response` verbatim plus a
  humanised summary. No direct `WorkService` access. Ever.

### Phase 6 — Interaction layer
- `interfaces/interaction/interaction_layer.py` — `InteractionLayer`
  that:
  1. accepts `InteractionInput`,
  2. runs the command interpreter,
  3. for CONTROL actions → dispatches through `WorkControlAdapter`,
     resolves target `work_id` from `InteractionSession.focused_work_id`
     (or from explicit payload),
  4. for `SEND_MESSAGE` → routes to `Orchestrator.route_request(
     "cognition", ...)` (or configured default capability),
  5. reads latest activity + status via the extended `status` handler,
  6. returns `InteractionOutput` carrying utterance + structured state
     + activity strip snapshot.
- The layer never touches `WorkService`, `WorkRepository`, or
  persistent stores.

### Phase 7 — Interaction test suite (text-only)
- `tests/test_s19_interaction_commands.py`
- `tests/test_s19_interaction_state_mapping.py`
- `tests/test_s19_activity_mapping.py`
- `tests/test_s19_work_control.py` — uses a real `WorkCapability` with
  in-memory repo + mock orchestrator target capabilities.
- `tests/test_s19_interaction_layer.py` — full text-mode interaction
  including pause/resume/redirect/approve/reject/input/takeover.

### Phase 8 — Presence
- `interfaces/presence/contracts.py`
  - `PresenceState` enum per spec §12
  - `PresenceFrame` (immutable state snapshot: state + activity lines
    + optional prompt)
  - `PresenceRenderer` protocol
- `interfaces/presence/derivation.py` — pure function
  `interaction_state_to_presence_state(NAVInteractionState) ->
  PresenceState`.
- `interfaces/presence/terminal_renderer.py` — `TerminalPresenceRenderer`,
  stdlib only. Frame-per-render, no threads, no animation loop for now.
- `tests/test_s19_presence.py` — verifies mapping and that the renderer
  produces distinct text for distinct states without touching a TTY.

### Phase 9 — Voice adapter (does not modify VoiceInterface)
- `interfaces/voice/interaction_voice_adapter.py` — `InteractionVoiceAdapter`
  that composes STT + TTS + mic + speaker with an `InteractionLayer`.
  This is the S19 voice path. `VoiceInterface` remains untouched for
  backward compatibility with S4/S9/S10 tests and callers.
- `tests/test_s19_voice_adapter.py` — end-to-end mocked (FakeMic + MockSTT
  + MockTTS + FakeSpeaker), proves voice → interaction → work control
  → TTS.

### Phase 10 — End-to-end integration
- `demo_s19.py` — root demo mirroring `demo_s10.py` precedent. Wires:
  registry, orchestrator, work + cognition + memory capabilities,
  interaction layer, terminal presence renderer. Text-mode REPL by
  default; `--voice` flag enables the voice adapter.
- `tests/test_s19_end_to_end.py` — text-mode end-to-end covering the
  full spec §33 example flow (create → work → pause → redirect →
  approval → resume → complete).

### Phase 11 — Documentation + release
- `docs/s19/implementation.md`
- `docs/s19/architectural_change_notes.md`
- `docs/s19/completion-report.md`
- Full validation: `ruff check .`, `mypy`, `pytest`.
- Merge, tag `v1.9`, push.
- `docs/s19/post_completion-report.md` after merge.

## Test coverage matrix (spec §30)

| Spec §30 category | Test file |
|---|---|
| Interaction tests (text → interaction, command mapping) | `test_s19_interaction_commands.py`, `test_s19_interaction_layer.py` |
| Control integration (all 9 control actions) | `test_s19_work_control.py`, `test_s19_interaction_layer.py` |
| State mapping | `test_s19_interaction_state_mapping.py` |
| Activity | `test_s19_activity_mapping.py`, `test_s19_status_activity.py` |
| Voice adapter (mocked STT/TTS) | `test_s19_voice_adapter.py` |
| Presence | `test_s19_presence.py` |
| End-to-end | `test_s19_end_to_end.py` |

## Non-goals (spec §31 recap)

- No photorealistic avatar. No lip-sync. No face rig.
- No new agent framework. No model-router changes.
- No WorkService rewrite. No second Work state machine.
- No security enforcement (that is S20).

## Commit cadence

Roughly 5 commits, per spec §36:

1. `S19: recon + baseline + plan + ADR 0008`
2. `S19: additive WorkCapability.status include_activity`
3. `S19: interaction contracts, session, commands, mappings, control adapter, layer + tests`
4. `S19: presence contracts, derivation, terminal renderer + tests`
5. `S19: voice adapter + demo + end-to-end tests + implementation/completion docs`

Final: merge to `main`, tag `v1.9`, push tag.
