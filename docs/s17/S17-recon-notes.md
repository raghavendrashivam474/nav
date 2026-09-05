# S17 Reconnaissance Notes — Technical Intelligence & Agentic Workflows

## 1. Context & Executive Summary

S17 transitions NAV from:
> "NAV can understand, remember, investigate, and resume work."
to:
> "NAV can take a goal, reason about the work required, construct a bounded plan, execute authorized steps through existing capabilities, observe results, verify progress, and iterate."

This recon answers all 25 questions established by the S17 specification before implementation begins.

---

## 2. Answers to Recon Questions

### Architecture
1. **Where should Work/Technical Intelligence live?**
   - Contract models and protocols in `core/contracts/work.py` (re-exported in `core/contracts/__init__.py`).
   - Implementation in `capabilities/work/` containing models, persistence, execution service, planning, evaluation, and capability wrapper.
2. **Does an appropriate existing contract already exist?**
   - No. Existing contracts cover Capabilities (`Request`/`Response`), Context (`NavContext`), Memory (`MemoryCapabilityInterface`), and Research (`ResearchCapabilityInterface`). A Work contract is needed.
3. **How are capabilities currently invoked?**
   - Core `Orchestrator` delegates to `CapabilityRegistry.get(name).invoke(Request(...)) -> Response(...)`.
   - Typed services also expose protocols (e.g. `ResearchExecutor`, `MemoryCapabilityInterface`).
   - The Work capability will invoke capabilities via `Orchestrator` / `CapabilityRegistry` using standard `Request`/`Response` and service delegates.
4. **What is the smallest extension required?**
   - Core contracts: `Work`, `WorkPlan`, `WorkStep`, `WorkStatus`, `StepStatus`, `WorkActivity`, `WorkActivityType`.
   - Persistence: `WorkRepository` ABC and `SQLiteWorkRepository` storing work lifecycle, plan steps, and activity log.
   - Planning: `Planner` interface, `DeterministicPlanner` for rule-based workflows, and `AIPlanner` utilizing `AIGateway`.
   - Execution: `WorkService` executing single steps or bounded loops with step evaluation and dependency validation.
   - Capability: `WorkCapability` registered in `CapabilityRegistry`.
5. **Can existing orchestration support the first version?**
   - Yes. The `Orchestrator` routes requests via `CapabilityRegistry`. `WorkCapability` plugs in cleanly.
6. **Does Work need persistence immediately?**
   - Yes. Goal-directed multi-step work must survive process restarts and remain inspectable, auditable, and resumable.
7. **What existing result/error abstractions can be reused?**
   - Standard `Response` (with `data`, `success`, `error`), and capability-specific outputs (`ResearchResult`, `MemoryRecord`).

### Planning
8. **What is the minimum representation of a plan?**
   - `WorkPlan(plan_id: str, version: int, steps: tuple[WorkStep, ...], created_at: str, metadata: dict)`.
9. **What is a work step?**
   - `WorkStep(step_id: str, name: str, description: str, capability: str, input_payload: dict, status: StepStatus, dependencies: tuple[str, ...], result: dict, error: str | None, started_at: str | None, completed_at: str | None, retry_count: int, max_retries: int)`.
10. **How is step ordering represented?**
    - Via step sequence in the plan combined with explicit dependency declarations.
11. **How are dependencies represented?**
    - `dependencies: tuple[str, ...]` listing prerequisite `step_id`s that must have `StepStatus.COMPLETED`.
12. **How does a step know what capability to invoke?**
    - The `capability` string identifies the target capability in `CapabilityRegistry` (e.g. `"research"`, `"memory"`, `"cognition"`).
13. **How is the result captured?**
    - The invocation output is stored in `WorkStep.result` (dict) and `WorkStep.error` (str | None).

### Execution
14. **How does a work run start?**
    - `work = work_service.create_work(objective=..., plan=...)` followed by step-by-step `work_service.execute_next_step(work_id)` or `work_service.run_bounded(work_id, max_steps=N)`.
15. **How does it advance to the next step?**
    - Finds the next `PENDING`/`READY` step whose dependencies are all `COMPLETED`, transitions it to `RUNNING`, executes it, records the result, updates status to `COMPLETED` (or `FAILED`), evaluates overall work progress, and picks the next step.
16. **How does it detect completion?**
    - When all steps are `COMPLETED` and evaluation confirms the objective is satisfied, `WorkStatus` transitions to `COMPLETED`.
17. **How does it handle failure?**
    - Failed steps record the error, set `status = StepStatus.FAILED`. If retries remain, can be retried. If not, the work transitions to `FAILED` or `BLOCKED`/`WAITING_FOR_INPUT`. No silent infinite loops.
18. **How does it handle retry?**
    - `work_service.retry_step(work_id, step_id)` increments `retry_count` and resets status to `READY`.
19. **How does it know when human input is required?**
    - If a step result indicates ambiguity, missing required inputs, or explicit escalation, status transitions to `WAITING_FOR_INPUT`.

### Continuity
20. **Can a work state be reconstructed after interruption/process restart?**
    - Yes, `SQLiteWorkRepository.get(work_id)` completely restores the `Work`, its `WorkPlan`, all step statuses, results, and activity log.
21. **What state must be persisted?**
    - ID, objective, status, context linkages (`project_id`, `goal_id`, `investigation_id`), plan steps, dependencies, results, errors, timestamps, and activity log.
22. **Can S16 investigation continuity remain independent?**
    - Yes. `Investigation` remains the persistent intellectual artifact. `Work` represents execution process. Work can create or link to an investigation without merging data models.

### Future S18/S19
23. **What state will S18 need for pause/stop/redirect?**
    - Explicit statuses (`PAUSED`, `CANCELLED`, `WAITING_FOR_INPUT`), step-level execution checkpoints (no monolithic loops), and methods to revise plans or pause execution between steps.
24. **What activity information will S19 need for visible status?**
    - `WorkActivity` records with granular timestamps, `activity_type`, human-readable descriptions, and metadata.
25. **Can those future requirements be supported without prematurely building the UI/control system?**
    - Yes, by establishing clean backend state models and event/activity logs.

---

## 3. Boundary & Non-Goals Checklist
- [x] No frontend or visual presence (deferred to S19).
- [x] No full human-control intervention system (deferred to S18).
- [x] No security-plane implementation (deferred to S20).
- [x] No multi-device sync (deferred to S21).
- [x] No vector database addition.
- [x] No monolithic "agent" class.
- [x] Deterministic execution first, AI-assisted planning behind existing `AIGateway`.
