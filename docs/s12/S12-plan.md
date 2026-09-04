# S12 — Context Foundation: Sprint Plan

## Sprint
**S12 — Context Foundation**

## Target Release
**v1.2**

## Starting Baseline
**NAV v1.1 — S11 officially closed**

## Objective
Establish a small, correct Context Foundation that represents the user's
current situation without conflating Context with Memory, Session, or
Research state.

## Motivation
NAV v0 already has conversation, cognition, voice, research, memory,
AI routing, research continuity, sessions, provenance, and caching.
However, NAV currently lacks a general mechanism for answering:

> "What is relevant about the user's current situation right now?"

This is distinct from Memory ("what has been retained?"), Session
("what interaction are we continuing?"), and Identity ("who is
participating?").

## Scope

### In Scope
1. **User Context** — stable/semi-stable preferences and constraints
2. **Active Projects** — what the user is currently working on
3. **Goals** — things the user is trying to accomplish
4. **Commitments** — things the user has explicitly identified as mattering
5. **Current Focus / Situation** — project, goal, activity, topic, priorities

### Out of Scope (Deferred)
- Memory intelligence (S13): importance, semantic retrieval, lifecycle
- Personal Context Integration (S14): Memory → Context relevance pipeline
- Research Partner (S15): persistent investigations, hypotheses
- Investigation Continuity (S16): long-term investigation continuation
- Technical Intelligence (S17): planning, architecture, verification
- Knowledge graphs, vector DBs, graph DBs, event infrastructure
- Orchestrator rewrite or major Core rewrite
- Inferred/autonomous context (all S12 context is explicit)

## North Star
> "Can NAV establish a reliable, lightweight context foundation that
> represents the user's current situation without turning Context into
> Memory, Session, or a giant knowledge graph?"

## Key Architectural Constraints
- Memory ≠ Context
- Session ≠ Context
- Identity ≠ Voice Identity
- Research owns its own ResearchContextStore
- S11 ContextManager ABC must not be casually redesigned
- All 246 existing tests must remain green

## Definition of Done
- [ ] Concrete ContextManager implementation exists
- [ ] Personal context models (Project, Goal, Commitment, CurrentFocus) defined
- [ ] NavContext snapshot includes optional personal_context
- [ ] ContextStore provides in-memory storage
- [ ] All new tests pass
- [ ] All existing tests pass (0 regressions)
- [ ] Ruff clean, format clean, Mypy clean
- [ ] ADR documenting NavContext extension
- [ ] S12 completion report
