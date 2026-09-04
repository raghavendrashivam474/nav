# ADR-006: Personal Context Model in NavContext

## Status
Accepted

## Context
S11 established the ContextManager ABC and NavContext snapshot but
deferred personal context (projects, goals, commitments, focus) to S12.
The existing NavContext had an mbient_data dict that could serve as
a catch-all, but the S12 brief explicitly calls for a typed
personal_context field to avoid unstructured sprawl.

## Decision
1. Add frozen dataclasses Project, Goal, Commitment, CurrentFocus,
   and PersonalContext to core/contracts/context.py.
2. Add personal_context: PersonalContext | None = None to NavContext.
3. Implement DefaultContextManager with concrete personal-context methods
   beyond the S11 ABC, keeping the ABC unchanged.
4. Use an in-memory ContextStore with no external dependencies.

## Consequences
- Backward compatible: personal_context defaults to None.
- The S11 ContextManager ABC is unchanged; S13/S14 may extend it via a
  future ADR if abstract personal-context methods are needed.
- All S12 personal context is explicit (user-declared).  Inference is
  deferred to S13/S14.
- No new database, graph, or external service introduced.
