# Sx1.2 — Implementation & Hardening Details

**Sprint:** Sx1.2
**Scope:** Orchestrator, Capability Dispatch, Work Execution Subsystem, SQLite Repository

---

## 1. Architectural Changes Overview

### A. Orchestrator Dispatch (`core/orchestration/orchestrator.py`)
- **REQUIRE_APPROVAL Interception:** Added guard clause checking `decision.outcome == AuthorizationOutcome.REQUIRE_APPROVAL`. If `_security_approved` is not truthy, Orchestrator halts execution and returns structured error response.
- **Deep-Copy Snapshot:** Payload is cloned using `copy.deepcopy()` prior to authorization evaluation, preventing in-flight dictionary tampering between check and invoke.
- **Actor Context Attachment:** The validated `ActorIdentity` is injected into the outbound payload as `_security_actor` for downstream capability observability.

### B. Work Service (`capabilities/work/service.py`)
- **Initiating Actor Persistence:** `create_work()` accepts `actor: Any` and stores it cleanly under `work.metadata["initiating_actor"]`.
- **Step Actor Propagation:** `_invoke_capability(step, work)` extracts the initiating actor from `work.metadata` and includes it in `payload["_actor"]` when routing step requests via Orchestrator, preventing confused-deputy context drops.

### C. SQLite Repository Serialization (`capabilities/work/sqlite_repo.py`)
- **JSON Serialization Fallback:** Added `_json_default()` hook to `json.dumps()` in `_work_to_data_blob()` to convert `ActorIdentity`, dataclasses, and Enums into JSON-serializable structures before persisting to SQLite.

### D. Human Interaction Control Gate (`interfaces/interaction/work_control.py`)
- **User Action Approval Assertion:** High-level human user commands coming through `WorkControlAdapter.execute_control()` are tagged with `_security_approved: True` to indicate legitimate human authority.
