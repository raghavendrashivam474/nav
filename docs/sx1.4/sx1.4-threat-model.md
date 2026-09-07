# Sx1.4 Threat Model: Service & Execution Boundary

## 1. System Overview & Deployment Model
NAV is currently an in-process, single-runtime agent system operating in a trusted local environment.
Requests enter through interaction adapters (text / voice / API) and are routed via the central `Orchestrator`.

## 2. Trust Boundaries
[ Untrusted External Input ]
│
(Trust Boundary)
▼
Orchestrator (Security Gate)
│ Evaluates PolicyEngine (ALLOW / DENY / REQUIRE_APPROVAL)
│ Sanitizes ActorIdentity & Attaches _security_actor
▼
Capability Layer (WorkCapability, MemoryCapability, etc.)
│
Service Layer (WorkService, MemoryService, etc.)
│ Internal trusted subsystem
▼
Repository & Storage Layer (SQLite, Local DB)
│
Execution Sinks (Database mutations, external calls)

text


## 3. Threat Assumptions
1. **Host Boundary**: The OS and Python process memory space are considered trusted. Memory-level bytecode tampering is out of scope for this tier.
2. **Actor Input**: All payload dictionary inputs arriving from external callers are untrusted and must be validated before reaching capability/service layers.
3. **Internal Components**: Capability implementations, services, and repositories are internal components running in the same process.
4. **Deputy Invariant**: When a service dispatches nested execution (e.g. `WorkService` running a multi-step plan via `_invoke_capability`), it MUST propagate the verified `_actor` context to prevent confused deputy privilege escalation.

## 4. Attack Vectors Analyzed
- **Direct Service Access**: Calling `WorkService` directly without orchestrator checks.
- **Direct Repo Access**: Manipulating persistence blobs in SQLite directly.
- **Approval Bypass**: Executing sensitive actions (`work.cancel`, `work.redirect`, `work.take_over`) without human approval.
- **Actor Tampering**: Forging `ActorType.SYSTEM` in payload dicts or custom identity objects.
- **Context Loss**: Dropping actor identity across multi-step execution.
