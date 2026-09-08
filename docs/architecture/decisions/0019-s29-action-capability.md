# ADR-0019: S29 Action Capability

## Status
Accepted

## Context
NAV's cognitive trajectory (S23–S28) established Acquire → Represent →
Synthesize → Compare → Reason → Decide. S28 Decision selects alternatives
but deliberately stops before execution. S29 introduces the Action
primitive to cross from cognition into controlled external effect.

## Decision
Introduce a first-class Action capability with:
- Explicit action types (initially ECHO and LOG)
- Deterministic state machine (REQUESTED → VALIDATED → AUTHORIZED →
  EXECUTING → terminal)
- Fail-closed authorization using existing Sx1 contracts
- Bounded execution via typed adapters
- No arbitrary code execution
- No model-driven security decisions

## Consequences
### Positive
- NAV can now perform explicitly authorized operations
- Action lifecycle is fully inspectable
- Clear separation between Decision (what) and Action (how)
- Foundation for future richer execution

### Negative
- Initial action set is very small (by design)
- No persistence means no audit trail yet
- Default authorizer is simplistic

### Risks
- Future expansion of action types must maintain security boundaries
- Model integration must preserve untrusted-output principle
