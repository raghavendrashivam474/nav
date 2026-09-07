# Sx1.4 Reconnaissance Report

## Repository State
- Branch: main @ aced3d6 (vx1.3)
- Synced with origin/main
- Working tree clean
- Frozen baselines: vx1.1 (f782ddf), vx1.2 (819cf86), vx1.3 (aced3d6)

## Test Baseline (pre-Sx1.4)
- Sx1.3: 31 passed
- Sx1.2: 11 passed
- S22: 22 passed
- Full suite: 793 passed, 1 skipped, 2 deselected

## Architecture Discovered

### Authorization Enforcement
Authorization is enforced at exactly ONE point:
  Orchestrator.route_request() -> SecurityService.authorize()

### Trust Flow
  External Input
       |
  Orchestrator.route_request()
       |-- sanitize actor (dict -> ActorIdentity, strip trust, downgrade SYSTEM)
       |-- deep-copy payload (prevent post-authz tampering)
       |-- SecurityService.authorize(actor, action, resource)
       |-- PolicyEngine.evaluate() -> ALLOW / DENY / REQUIRE_APPROVAL
       |-- attach _security_actor to payload
       |
  CapabilityRegistry.get() -> Capability.invoke(request)
       |
  WorkCapability._handle_*()  [NO authorization checks]
       |
  WorkService.*()             [NO authorization checks]
       |
  WorkRepository.*()          [NO authorization checks]
       |
  SQLite DB / Execution

### Key Components
| Component | Lines | Authz? | Notes |
|-----------|-------|--------|-------|
| Orchestrator | 171 | YES | Single enforcement point |
| SecurityService | 122 | YES | Policy evaluation, event logging |
| PolicyEngine | 187 | YES | Deterministic rule matching |
| WorkCapability | 303 | NO | Trusts Orchestrator |
| WorkService | 864 | NO | Assumes authorized caller |
| WorkRepository | 43 | NO | Abstract data interface |
| SQLiteWorkRepo | 318 | NO | Pure persistence |

### Policy Rules (Default)
1. SYSTEM actor: ALLOW * (priority 100)
2. USER: REQUIRE_APPROVAL for cancel/redirect/take_over/delete (priority 50)
3. USER: ALLOW * (priority 10)
4. AGENT: REQUIRE_APPROVAL for cancel/redirect (priority 50)
5. AGENT: DENY take_over (priority 50)
6. AGENT: ALLOW * (priority 10)
7. Default: DENY (fail-closed)

## Section 21 Answers

### A. Execution entry points
- Orchestrator.route_request() (primary, authorized)
- WorkCapability.invoke() (via registry, post-authz)
- WorkService.* methods (internal, no authz)
- WorkRepository.* methods (internal, no authz)

### B. Services directly invocable
- WorkService: all methods (create, cancel, delete, redirect, take_over, etc.)
- SecurityService: authorize() (defaults to SYSTEM if no actor)

### C. Capabilities directly invocable
- WorkCapability: all 18 action handlers
- Any capability registered in CapabilityRegistry

### D. Paths bypassing Orchestrator
- Direct WorkService instantiation + method call
- Direct WorkRepository instantiation + method call
- Direct WorkCapability.invoke() without Orchestrator

### E. Reachable by untrusted actors?
- In current in-process model: NO
- No network/API surface exposes WorkService directly
- All external input flows through Orchestrator

### F. Internal trusted APIs?
- WorkService is an internal trusted API
- WorkRepository is an internal trusted API
- SecurityService.authorize() is an internal trusted API

### G. Operations mutating privileged state
- WorkService: cancel_work, delete_work, redirect_work, take_over,
  approve_step, reject_step, revise_plan, set_status

### H. Operations causing execution
- WorkService: execute_next_step, run_bounded, auto_plan

### I. Where authorization is enforced
- ONLY in Orchestrator.route_request()

### J. Actor context propagation
- Orchestrator attaches _security_actor to payload
- WorkCapability reads _security_actor or falls back to _actor
- WorkService.create_work accepts actor parameter
- Other WorkService methods do NOT receive or check actor

### K. Where actor context disappears
- WorkService.cancel_work, pause_work, resume_work, delete_work,
  redirect_work, take_over, return_control: NO actor parameter
- These methods operate on work_id alone

### L. Where new actor context can be manufactured
- SecurityService.authorize() defaults to SYSTEM_ACTOR if actor=None
- Any direct caller of SecurityService can omit actor

### M. Async execution
- Not observed in current codebase
- WorkService.run_bounded is synchronous

### N. Post-persistence execution
- Work can be reloaded from SQLite and executed
- No re-authorization on reload

### O. Contractual vs conventional boundaries
- CONTRACTUAL: Orchestrator -> SecurityService (enforced in code)
- CONVENTIONAL: "Callers should use Orchestrator" (not enforced)
- CONVENTIONAL: WorkService is internal-only (not enforced)
