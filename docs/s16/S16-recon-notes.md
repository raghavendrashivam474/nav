# S16 Recon Notes

## Investigation state
1. All core fields (findings, hypotheses, sources, evidence, conflicts, uncertainties, open_questions) are persisted in the JSON data blob.
2. Missing: structured activity history. Only `updated_at` exists, which changes on any mutation (even tag edits).
3. Timestamps are ISO-8601 strings, sufficient for ordering.
4. Cannot currently determine most recent *meaningful* research activity vs. metadata changes.
5. Can distinguish findings from open questions — they are separate fields.

## Continuation
6. Resolution: match by title substring, tags, project_id, goal_id, objective text, or exact ID.
7. Multiple matches: surface ambiguity, do not silently choose.
8. No match: return explicit "none" confidence, suggest new investigation.
9. "Resume" = load + reconstruct + present. "Continue" = resume + user chooses + research.
10. Continuation snapshot: derived, deterministic, read-only view of investigation state.

## Research
11. `conduct_research()` already merges into existing investigation — reuse as-is.
12. Existing method supports continuation; just needs activity logging.
13. No Research contract changes needed.

## Context
14. Current context can inform resolution (project_id, goal_id, tags).
15. Read-only: context informs matching but does not mutate the investigation.
16. Remains read-only.

## Memory
17. Memory does NOT need to participate. Investigation is already persistent.
18. Clean separation: Memory = what to remember, Investigation = what we're studying.

## Orchestration
19. Orchestrator integration deferred — S16 provides the service layer; wiring is future work.
20. No architectural change to Orchestrator required.

## Architecture
21. S16 is fully additive.
22. No insufficiency found.
23. Smallest improvement: add activity_log to Investigation model + new continuity subpackage.
