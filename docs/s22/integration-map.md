# S22 — Integration Map

> Validated during S22 Phase 2-4 reconnaissance and scenario execution.

## Actual v1 Request Path

```text
USER
 │
 ▼
Voice / Text Input                              [EXISTS]
 │
 ▼
Interaction Layer (interfaces/interaction/)      [EXISTS]
 │  ├── CommandInterpreter (text → UserAction)   [EXISTS]
 │  ├── InteractionSession (focus, state)        [EXISTS]
 │  └── WorkControlAdapter (action → request)    [EXISTS]
 │
 ▼
Request Object (core.contracts.capability)       [EXISTS]
 │
 ▼
Orchestrator (core/orchestration/)               [EXISTS]
 │
 ├──── SecurityService (core/security/)          [EXISTS]
 │          ├── PolicyEngine                     [EXISTS]
 │          ├── AuthorizationDecision            [EXISTS]
 │          └── SecurityEventLog                 [EXISTS]
 │
 ▼
CapabilityRegistry.get(target)                   [EXISTS]
 │
 ▼
WorkCapability → WorkService                     [EXISTS]
 │
 ├── create_work / set_plan / auto_plan          [EXISTS]
 ├── execute_next_step / run_bounded             [EXISTS]
 ├── pause / resume / cancel                     [EXISTS]
 ├── redirect / revise_plan                      [EXISTS]
 ├── approve / reject / provide_input            [EXISTS]
 ├── take_over / return_control                  [EXISTS]
 └── status (→ current_step_id, activity)        [EXISTS — S22 FIX]
 │
 ▼
SQLiteWorkRepository (persistence)               [EXISTS]
 │
 ▼
InteractionOutput (voice/text/presence)          [EXISTS]
 │
 ├── Voice: InteractionVoiceAdapter              [EXISTS]
 ├── Text: InteractionLayer.process_input        [EXISTS]
 └── Presence: TerminalPresenceRenderer          [EXISTS]
```
## Cross-cutting Concerns
```text

NavContext propagation                           [MISSING — not wired through Orchestrator]
Environment/Device/Runtime identity (S21)        [PARTIAL — contracts exist, not in request path]
Error/failure propagation                        [EXISTS — Response.success + error field]
Activity/status observability                    [EXISTS — WorkActivity log, status endpoint]
```
## S21 Integration Status
```text

EnvironmentIdentity                              [EXISTS — standalone, non-interfering]
DeviceIdentity                                   [EXISTS — standalone]
RuntimeIdentity                                  [EXISTS — standalone]
RuntimeRegistry                                  [EXISTS — in-memory]
StateOrigin                                      [EXISTS — metadata contract]
Wired into Orchestrator                          [NOT YET — deferred, not v1-critical]
Wired into WorkService                           [NOT YET — deferred, not v1-critical]
```