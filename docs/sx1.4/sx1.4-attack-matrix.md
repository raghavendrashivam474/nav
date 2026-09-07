# Sx1.4 Attack Matrix

| ID | Attack Family | Initial State | Classification | Evidence | Fix / Status | Residual Risk |
|---|---|---|---|---|---|---|
| ATK-01 | Direct Service Invocation | Unchecked | ARCHITECTURAL WEAKNESS | `WorkService.cancel_work` callable directly | Maintained as internal trusted API; callers go through Orchestrator | Untrusted code within runtime could call directly |
| ATK-02 | Direct Repository Manipulation | Unchecked | ARCHITECTURAL WEAKNESS | `SQLiteWorkRepository.update` modifies state directly | Enclosed within service module | Raw SQLite access bypasses lifecycle |
| ATK-03 | Capability -> Service Boundary Bypass | Checked | BLOCKED | `Orchestrator.route_request` sanitizes actor & checks policy | Sx1.1/Sx1.2 enforcement verified | Direct invoke bypasses if unrouted |
| ATK-04 | Service -> Capability Re-entry | Isolated | NOT APPLICABLE | `WorkService` has no registry reference | Re-entry dispatches via Orchestrator | None |
| ATK-05 | Authorization Boundary Skipping | Documented | ARCHITECTURAL WEAKNESS | Orchestrator is the single enforcement point | Documented boundary architecture | Non-orchestrator callers skip policy |
| ATK-06 | Alternate Execution Entry Points | Verified | ARCHITECTURAL WEAKNESS | Internal helper methods bypass auth | Orchestrator wraps all public routes | Internal calls must remain trusted |
| ATK-07 | Lifecycle Bypass | Unchecked internally | ARCHITECTURAL WEAKNESS | Direct lifecycle calls mutate status without auth | Orchestrator policy enforces approval | Direct Python API usage |
| ATK-08 | Approval Boundary Bypass | Enforced | BLOCKED | `Orchestrator` halts on `REQUIRE_APPROVAL` | Sx1.2 verification tests passing | Direct service calls omit check |
| ATK-09 | Context Stripping | Sanitized | BLOCKED | Missing actor defaults to anonymous | Sanitized at orchestrator level | Direct security service defaults SYSTEM |
| ATK-10 | Context Forgery | Sanitized | BLOCKED | Dict/object SYSTEM claims downgraded to USER | Sx1.3 validation rules active | None |
| ATK-11 | Confused Deputy | Enforced | BLOCKED | Initiating actor attached in step payload | `_invoke_capability` propagates actor | Custom step payloads must be monitored |
| ATK-12 | Privileged Internal Caller | In-process | ARCHITECTURAL WEAKNESS | `SecurityService.authorize()` defaults SYSTEM if None | Expected backward compatibility | Untrusted caller calling SecurityService |
| ATK-13 | Error / Exception Boundary | Fail-Closed | BLOCKED | Exception in auth returns error response | Fail-closed pattern across routing | None |
| ATK-14 | Nested Execution Composition | Propagated | BLOCKED | `_invoke_capability` carries `initiating_actor` | Tested across work steps | None |
| ATK-15 | Execution Sink Discovery | Data sinks only | NOT APPLICABLE | Sinks are SQLite storage only | No OS/subprocess/network sinks | Future hardware actuators need guards |
