# S29 Reconnaissance Notes

## Repository Structure
- Core contracts in `core/contracts/`
- Capabilities in `capabilities/<name>/` with engine.py, service.py, capability.py
- Security contracts in `core/contracts/security.py` (Sx1 closed)
- Security implementation directory `security/` is empty (contracts only)
- Tests in `tests/`

## S28 Decision Architecture
- Frozen dataclasses with __post_init__ validation
- DecisionState enum: DECIDED, CONTESTED, INCONCLUSIVE, INSUFFICIENT_INPUTS, NO_FEASIBLE_ALTERNATIVE
- Engine: deterministic-first, model-assisted fallback
- Service: facade composing engine + sibling services
- Capability: implements Capability ABC (name, version, description, invoke)
- S28 deliberately stops at selection — no execution

## Existing Security (Sx1)
- ActorIdentity(actor_id, actor_type, trust_level, metadata)
- AuthorizationRequest(actor, action, resource, context)
- AuthorizationDecision(outcome, actor_id, action, resource, reason, policy_ref)
- AuthorizationOutcome: ALLOW, DENY, REQUIRE_APPROVAL
- SYSTEM_ACTOR: trust_level=100
- No enforcement engine in security/ directory — enforcement at capability level

## Integration Opportunities
- ActionEngine can accept AuthorizerFn callable using existing AuthorizationRequest/Decision
- ActionRequest can link to DecisionResult via decision_id
- MappingProxyType pattern from security.py for freezing dicts

## Risks
- Security enforcement is contract-level only; no policy engine exists
- Default authorizer must fail closed
- Must not introduce arbitrary code execution

## Open Questions
- None requiring architectural changes. Sx1 contracts are sufficient for S29.
