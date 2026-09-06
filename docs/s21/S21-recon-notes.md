# S21 Reconnaissance Notes

## Identity (Q1-4)
1. NAV has NO persistent environment identity. Only SYSTEM_ACTOR (actor_id="nav:system").
2. Actors identified by ActorIdentity(actor_id, actor_type, trust_level, metadata).
3. Two runtime instances CANNOT distinguish themselves. No runtime identity exists.
4. No persistent installation/runtime identity. Everything is in-memory or process-scoped.

## State (Q5-8)
5. ALL state is local: ContextStore (in-memory), Memory/Work/Investigations (SQLite), SecurityEventLog (in-memory).
6. Conceptually environment-owned: personal context, memory, investigations, work, preferences.
7. Device-local: ContextStore, SecurityEventLog, session state, hardware config.
8. YES — Orchestrator, Work, Context, Interaction all assume single process/device.

## Persistence (Q9-11)
9. SQLite: capabilities/memory/sqlite_repo.py, capabilities/work/sqlite_repo.py, capabilities/research/investigation/sqlite_repo.py.
10. Identifiers are string UUIDs. No environment scoping.
11. No — repositories cannot distinguish local from shared state.

## Execution (Q12-15)
12. Orchestrator: single-runtime. No environment context in routing.
13. Work: single-runtime. No origin tracking.
14. Context: single-runtime. Keyed by user_id/session_id only.
15. Interaction: single-runtime.

## Security (Q16-18)
16. ActorIdentity = WHO. Device/Runtime = WHERE. Complementary, not merged.
17. No claim mechanism exists. S21 establishes identity without granting trust.
18. EnvironmentIdentity, DeviceIdentity, RuntimeIdentity as frozen dataclasses. No auth required.

## Synchronization (Q19-21)
19. No synchronization abstraction exists.
20. Natural boundary: between SQLite repositories and future transport layer.
21. Smallest contract: StateOrigin (environment_id, origin_runtime_id, state_version, timestamp).
