# S29 Implementation Plan

## Architecture
1. Action contracts (ActionType, ActionState, ActionOutcome, ActionRequest, ActionResult)
2. Deterministic state machine with VALID_TRANSITIONS
3. ActionEngine with validation, authorization, and bounded execution
4. ActionService facade
5. ActionCapability for orchestrator integration

## Execution Adapters (initial)
- ECHO: returns parameters (no side effects, testing)
- LOG: structured log entry (safest real side effect)

## Security Integration
- AuthorizerFn callable accepting AuthorizationRequest, returning AuthorizationDecision
- Default authorizer: fail-closed, allows only trust_level >= 100
- Uses existing Sx1 contracts without modification

## Testing
- Contract tests, engine tests, service tests, capability tests
- Adversarial tests: auth bypass, parameter injection, escalation, fake success

## Files
- core/contracts/action.py
- capabilities/action/{__init__,engine,service,capability}.py
- tests/test_s29_action.py, test_s29_adversarial.py
- docs/s29/*
