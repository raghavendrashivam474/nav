# Sx1.4 Residual Security Risks

## Identified Risks & Boundaries

1. **Plugin / Third-Party Extension Ingress**:
   - *Risk*: If future NAV versions allow dynamic third-party plugins to execute within the same Python process, a plugin could import `WorkService` or `SQLiteWorkRepository` and bypass policy.
   - *Mitigation for Future Architecture*: Introduce capability isolation or sandboxing before third-party plugin support is enabled.

2. **SecurityService Default System Fallback**:
   - *Risk*: Calling `SecurityService.authorize()` with `actor=None` defaults to `SYSTEM_ACTOR` for backward compatibility with S17-S19.
   - *Mitigation*: Ensure all public entry points explicitly sanitize and provide `actor`. Deprecate `SYSTEM_ACTOR` fallback in future major version.

3. **In-Memory State Mutability**:
   - *Risk*: Python objects in the same process are mutable unless explicitly guarded.
   - *Mitigation*: Orchestrator performs defensive `copy.deepcopy()` of incoming payloads and wraps `ActorIdentity.metadata` in `MappingProxyType`.
