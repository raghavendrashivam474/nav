# S19 Reconnaissance Notes

**Sprint:** S19 — Interaction & Presence Model
**Baseline:** v1.8 (commit `72a8dfd`)
**Branch:** `sprint/s19-interaction-presence`
**Author:** S19 recon pass

This document answers the 20 recon questions from S19 spec §25 based on
direct inspection of the v1.8 tree. Nothing in this document assumes; every
answer is grounded in an inspected file.

---

## 1. Where does NAV currently start?

There is **no persistent NAV runtime entry point** at the repo root. The
only executable at the root is `demo_s10.py`, which manually wires the
`CapabilityRegistry`, registers capabilities, constructs an `Orchestrator`,
and runs a scripted + REPL loop.

`pyproject.toml` declares no `[project.scripts]` entry. There is no
`main.py`, `__main__.py`, `app.py`, `cli.py`, or `run.py` inside `core/`,
`capabilities/`, or `interfaces/`.

**Implication:** S19 will introduce a small `demo_s19.py` at the repo root
(mirroring the `demo_s10.py` precedent) that exercises the full
interaction + presence path. This is a demo, not a new runtime framework.

---

## 2. Is there already an interface layer?

Yes. `interfaces/` exists with two subpackages:

- `interfaces/text/` — empty (just `__init__.py`).
- `interfaces/voice/` — a fully built S4/S9/S10 voice stack.

`interfaces/voice/interface.py` defines `VoiceInterface`, which is
essentially the shape S19 needs to generalise: it does
`Microphone → STT → Orchestrator.route_request(capability, Request) → TTS → Speaker`.

Today `VoiceInterface` is hard-coded to route to a single capability
(default `"cognition"`) via one prompt payload. It has no notion of
Work control, active-work resolution, or interaction state.

**Implication:** S19 will introduce a new `interfaces/interaction/` package
that owns the interaction contract and command interpretation. `VoiceInterface`
will be extended (not replaced) in a later phase so voice input flows into
the new interaction layer instead of directly into cognition.

---

## 3. Is there already voice input?

Yes.

- `interfaces/voice/microphone.py` — `Microphone` (sounddevice) and
  `FakeMicrophone` (deterministic test double).
- `interfaces/voice/stt/` — `MockSTT` and `whisper_stt.py` plus a
  `factory.create_stt()`.
- `interfaces/voice/contracts.py` — `SpeechToText` ABC.

Voice extras are optional (`pip install -e ".[voice]"`).

**Implication:** S19 will *reuse* the STT boundary as-is. No new adapters.

---

## 4. Is there already speech output?

Yes.

- `interfaces/voice/speaker.py` — `Speaker` (sounddevice) and `FakeSpeaker`.
- `interfaces/voice/tts/` — `MockTTS`, `pyttsx3_tts.py`, `factory.create_tts()`.
- `interfaces/voice/contracts.py` — `TextToSpeech` ABC.

**Implication:** S19 will *reuse* the TTS boundary as-is.

---

## 5. What is the current input path?

For voice today:

    FakeMicrophone/Microphone.record() -> AudioInput
      -> SpeechToText.transcribe(audio) -> str
      -> VoiceInterface builds Request{payload={"prompt": ...}}
      -> Orchestrator.route_request("cognition", request)

There is no equivalent path for text. Text input today goes through
`demo_s10.py` which builds a `Request` directly and calls the orchestrator.

**Implication:** S19 introduces a single interaction boundary that both
voice and text feed into.

---

## 6. What is the current output path?

For voice:

    Response{data={"reply": "..."}}
      -> VoiceInterface reads reply
      -> TextToSpeech.synthesize(reply) -> AudioOutput
      -> Speaker.play(audio_out)

Cognition responses use `data["reply"]`. Research responses also use
`data["reply"]`. Work responses use structured fields like
`data["work_id"]`, `data["status"]`.

**Implication:** Interaction responses must carry both a human-facing
utterance (for TTS) and structured state (for the UI / activity strip).

---

## 7. How is WorkCapability currently accessed?

Via `Orchestrator.route_request("work", request)`. `WorkCapability.invoke()`
inspects `request.payload["action"]` and dispatches to one of 17 handlers.

The full action list (per `capabilities/work/capability.py`):

    create, plan, execute_step, run_bounded, status,
    pause, cancel, resume, request_intervention, revise_plan, redirect,
    approve, reject, request_input, provide_input,
    take_over, return_control

Every handler that mutates or inspects a specific Work item requires
`work_id` in the payload.

**Implication:** The interaction layer's control adapter builds `Request`
objects for these exact actions. It does **not** touch `WorkService` or
`WorkRepository`.

---

## 8. How can the active Work be resolved?

There is **no first-class "active work" concept** in the backend. `Work`
carries no "is_active" flag; `WorkService` exposes no `get_current_work()`.
`WorkQuery` supports filtering by status but not "focus".

Choices available to the interaction layer, in preference order:

1. **Session-scoped focus in the interaction layer:** remember the last
   `work_id` the user created / referenced within the interaction session.
2. Fallback: query `WorkCapability(action="status", work_id=...)` only
   when the user explicitly names one, or list running Work by status.

**Decision:** S19 implements (1) as a lightweight in-memory
`InteractionSession` that holds `focused_work_id`. This is a
**pure interaction-layer concern** — the backend gains no new fields, no
new state, and no new state machine. §23 forbids adding a second Work
state machine; a session-scoped focus pointer is not a state machine.

---

## 9. Where can WorkActivity be read?

`Work.activity_log` is a `tuple[WorkActivity, ...]` on every `Work`
instance, populated by `WorkService._record_activity`. Each
`WorkActivity` has `timestamp`, `activity_type: WorkActivityType`,
`description`, `step_id`, and `metadata`.

The interaction layer reads activity by calling
`WorkCapability(action="status", work_id=...)` — but that handler today
returns only `activity_count`, **not the log itself**.

**Gap identified.** Options:

- **A.** Add an `include_activity: bool` flag to the `status` action so the
  handler returns the latest N activity entries. Additive, non-breaking.
- **B.** Add a new `activity` action to `WorkCapability`. Also additive.
- **C.** Read `Work.activity_log` via a new method on `WorkService`.
  Rejected — that widens the service surface for a read-only concern.

**Decision:** Option **A** (extend the existing `status` handler with an
optional `include_activity` flag returning the last N structured entries).
This is a purely additive, backward-compatible extension to a single
handler. It does not change any state semantics, does not add a new
action, does not alter existing return payloads for callers that omit the
flag. This is documented in `architectural_change_notes.md` and is minor
enough that no ADR is required.

---

## 10. How are Work statuses currently exposed?

`WorkCapability(action="status")` returns:

    { work_id, objective, status (str), completed_steps, pending_steps, activity_count }

`WorkStatus` is a str-Enum with the 11 states listed in the spec §6.
`StepStatus` includes `WAITING_FOR_APPROVAL` and `WAITING_FOR_INPUT`.

The status string is the raw enum value (e.g. `"waiting_for_approval"`).

**Implication:** The interaction layer must map raw `WorkStatus` strings
to `NAVInteractionState` (spec §5, §15).

---

## 11. What state must the frontend observe?

Per spec §12:

    IDLE, LISTENING, THINKING, WORKING,
    WAITING_FOR_INPUT, WAITING_FOR_APPROVAL,
    PAUSED, RESPONDING, COMPLETED

Plus an implicit `ERROR` (spec §15 maps `FAILED → ERROR`).

Presence state is **derived** from interaction state, which is **derived**
from backend `WorkStatus` plus interaction-layer signals (LISTENING,
THINKING, RESPONDING come from the interaction layer itself, since the
backend has no concept of "the user is currently speaking").

---

## 12. What state must remain backend-owned?

All `WorkStatus`, `StepStatus`, `WorkActivityType` transitions. Approval
metadata. Control metadata (`work.metadata["control"]`). Plan versions.

The interaction layer owns only:
- `focused_work_id`
- Whether the mic is currently open (LISTENING)
- Whether NAV is currently synthesising / speaking (RESPONDING)
- Whether the interaction layer is currently issuing an
  orchestrator request (THINKING)

These are transient interaction-session properties, not persistent state.

---

## 13. What rendering technology is currently available?

None dedicated. The repo has:

- `pyttsx3`, `sounddevice`, `numpy`, `faster-whisper` as optional deps.
- No graphics library, no game engine, no web framework, no GUI toolkit.

Adding a heavyweight renderer contradicts spec §31 ("no huge graphics
engine"). The pragmatic first renderer is a **terminal renderer** using
only stdlib (`sys.stdout`, ANSI escapes) — or optionally `rich` (already
transitively available via pip's vendored copy, but not a direct
dependency). We will use pure stdlib to avoid adding a new direct
dependency.

**Decision:** First presence renderer is a `TerminalPresenceRenderer` that
emits state-driven ASCII / ANSI frames. The `PresenceRenderer` protocol
is designed so a future graphical renderer can replace it without
touching interaction semantics (spec §14).

---

## 14. Is there an existing UI framework?

No.

---

## 15. Can the existing interface be extended?

Partially. `interfaces/voice/interface.py::VoiceInterface` is a good
reference shape but is single-capability and single-payload-format. S19
does not need to modify it; S19 will introduce a peer
`interfaces/interaction/` package. A later phase optionally wires
`VoiceInterface` to feed the new interaction layer instead of cognition
directly.

For S19 we take the cleaner path: **the new interaction layer is its own
package**, and `demo_s19.py` composes STT → interaction → TTS explicitly
(mirroring how `VoiceInterface` composes today). We do **not** rewrite
`VoiceInterface`.

---

## 16. Would a new frontend boundary be cleaner?

Yes. Introducing `interfaces/interaction/` alongside `interfaces/voice/`
keeps concerns split:

- `interfaces/voice/` — audio I/O adapters (STT, TTS, mic, speaker).
- `interfaces/interaction/` — interaction contract, command interpreter,
  control adapter, activity mapping, interaction-state derivation,
  session focus.
- `interfaces/presence/` — presence state derivation, renderer protocol,
  terminal renderer.

`pyproject.toml`'s `packages.find` includes `interfaces*`, so these
packages are picked up automatically. Nothing in `core/` or
`capabilities/` needs to change to accommodate them.

---

## 17. What existing code can be reused?

- `Orchestrator.route_request` — the single dispatch path.
- `WorkCapability` — all 17 actions.
- `interfaces/voice/contracts.SpeechToText` / `TextToSpeech`.
- `interfaces/voice/microphone.MicrophoneProtocol`.
- `interfaces/voice/speaker.SpeakerProtocol`.
- `interfaces/voice/stt/mock_stt.MockSTT` for tests.
- `interfaces/voice/tts/mock_tts.MockTTS` for tests.
- `interfaces/voice/audio.AudioInput / AudioOutput`.
- `core.contracts.capability.Request / Response`.
- `core.contracts.work.WorkStatus / WorkActivity / WorkActivityType`.

---

## 18. What existing code must remain untouched?

- `capabilities/work/service.py` — WorkService state machine.
- `capabilities/work/repository.py`, `sqlite_repo.py` — persistence.
- `core/orchestration/orchestrator.py`.
- `core/capabilities/registry.py`.
- `core/contracts/work.py` — Work, WorkStatus, WorkStep, WorkActivity.
- All S17/S18 tests.

**One controlled exception:** `capabilities/work/capability.py`'s
`_handle_status` gains an optional `include_activity` flag (see Q9). No
signature-breaking change; existing callers get the same payload.

---

## 19. What architectural gap prevents S19 from being implemented cleanly?

Two small gaps, both resolvable additively:

1. **`WorkCapability.status` does not return activity entries.** Resolved
   by extending `_handle_status` with an optional `include_activity` flag
   (Q9). Additive, backward-compatible.
2. **No "active work" concept.** Resolved entirely inside the interaction
   layer via a session-scoped `focused_work_id`. No backend change.

Neither gap requires re-architecting S17/S18.

---

## 20. Is an ADR required?

Yes — a single ADR: **`0008-s19-interaction-boundary.md`**.

It captures:

- Why S19 introduces a distinct `interfaces/interaction/` package rather
  than extending `VoiceInterface`.
- Why "active work" is an interaction-session concept and not a backend
  field (protects §23).
- Why presence state is derived, not stored (protects §15).
- Why the first renderer is terminal-only.
- The `include_activity` extension to `WorkCapability.status`, with
  compatibility guarantees.

The ADR does **not** propose a change to any S17/S18 contract semantics.

---

## Summary of decisions this recon locks in

| # | Decision |
|---|----------|
| 1 | New package `interfaces/interaction/` — interaction contract + command interpreter + work-control adapter + activity mapping + state mapping + session focus. |
| 2 | New package `interfaces/presence/` — presence state derivation + `PresenceRenderer` protocol + `TerminalPresenceRenderer`. |
| 3 | Reuse `interfaces/voice/` STT + TTS + mic + speaker as-is. `VoiceInterface` is not modified in S19. |
| 4 | Introduce `demo_s19.py` at repo root as the end-to-end integration entry point. |
| 5 | Extend `WorkCapability._handle_status` with an optional `include_activity: bool` and `activity_limit: int` (default 2) returning the latest structured `WorkActivity` entries. Purely additive. |
| 6 | Active-work focus is an interaction-layer concept only. No backend fields added. |
| 7 | ADR 0008 documents the interaction boundary and the one additive backend touch. |
| 8 | First renderer is `TerminalPresenceRenderer` — stdlib only, no new direct dependencies. |
