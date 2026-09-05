# S19 Baseline

**Sprint:** S19 — Interaction & Presence Model
**Baseline tag:** `v1.8`
**Baseline commit:** `72a8dfd`
**Branch:** `sprint/s19-interaction-presence`
**Baseline captured:** at branch creation from `main` (fast-forward,
clean working tree).

## Protected baseline surface

Per S19 spec §5 / §23 / §38, the following are **frozen** for the
duration of S19 and must remain byte-for-byte identical except where
this sprint's `architectural_change_notes.md` explicitly authorises a
change.

### Frozen files

- `core/contracts/work.py`
- `core/contracts/capability.py`
- `core/contracts/context.py`
- `core/orchestration/orchestrator.py`
- `core/capabilities/registry.py`
- `capabilities/work/service.py`
- `capabilities/work/repository.py`
- `capabilities/work/sqlite_repo.py`
- `capabilities/work/planner.py`
- `capabilities/work/evaluator.py`
- All existing tests under `tests/test_s10_*.py`, `tests/test_s13_*.py`,
  `tests/test_s14_*.py`, `tests/test_s15_*.py`, `tests/test_s16_*.py`,
  `tests/test_s17_*.py`, `tests/test_s18_*.py`.
- `interfaces/voice/audio.py`
- `interfaces/voice/contracts.py`
- `interfaces/voice/errors.py`
- `interfaces/voice/interface.py`
- `interfaces/voice/microphone.py`
- `interfaces/voice/speaker.py`
- `interfaces/voice/progress.py`
- `interfaces/voice/stt/*`
- `interfaces/voice/tts/*`

### Controlled additive touch (authorised)

- `capabilities/work/capability.py` — `_handle_status` gains an optional
  `include_activity: bool = False` and `activity_limit: int = 2`. When
  `include_activity` is falsy, the response payload is byte-identical
  to the S18 payload. See `docs/s19/architectural_change_notes.md`.

### New surface introduced by S19

- `interfaces/interaction/` (new package)
- `interfaces/presence/` (new package)
- `demo_s19.py` (new root demo, mirrors `demo_s10.py` precedent)
- `tests/test_s19_*.py` (new tests)
- `docs/s19/*.md`
- `docs/architecture/decisions/0008-s19-interaction-boundary.md`

## Verification of baseline before S19 work
git status # clean
git rev-parse HEAD # 72a8dfd
git tag --contains 72a8dfd # includes v1.8
git rev-parse --abbrev-ref HEAD # sprint/s19-interaction-presence

text


## Compatibility guarantees

1. All S17/S18 tests remain green with no modification.
2. Existing callers of `WorkCapability` action `"status"` that do not set
   `include_activity` receive the identical response payload as S18.
3. No `WorkStatus`, `StepStatus`, or `WorkActivityType` enum values are
   added, removed, renamed, or re-semanticised.
4. `WorkService` public methods are not touched. `WorkRepository` is not
   touched.
5. `Orchestrator` is not touched.
6. The `interfaces/voice/` public surface is not touched. `VoiceInterface`
   continues to route voice → `Orchestrator.route_request("cognition", ...)`
   unchanged. S19's voice path is a **peer** adapter, not a replacement.
