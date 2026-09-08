# S28 Implementation Plan

1. **Reconnaissance**: Inspect S27 Reasoning and S26 Comparison contracts and AI Gateway.
2. **Contract Design**: Define `DecisionState`, `ConstraintType`, `DecisionAlternative`, `DecisionCriterion`, `AlternativeEvaluation`, `DecisionInput`, and `DecisionResult`.
3. **Engine Implementation**: Implement deterministic hard constraint filtering, auto-selection, AI-assisted trade-off synthesis, and safe fallback.
4. **Service & Capability**: Build `DecisionService` and `DecisionCapability` adhering to the Orchestrator/Request-Response pattern.
5. **Testing**: Add comprehensive contract, deterministic engine, model-assisted, service, capability, and adversarial tests.
6. **Verification**: Confirm 0 regressions on the full NAV test suite and 100% clean Ruff linting.
