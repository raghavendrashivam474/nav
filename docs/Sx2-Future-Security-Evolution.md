# Sx2 --- Future Security Evolution

**Status:** Preserved future scope\
**Relationship to Sx1:** Sx1 is closed and frozen; this document does
not reopen Sx1.\
**Purpose:** Preserve future security concerns identified during the Sx1
Blackbox for a potential future Sx2 campaign.

## 1. Scope

Sx1 established and adversarially validated NAV's current security
foundation across identity, authority, authorization, approval,
capability, work, persistence, service boundaries, execution, and
cross-boundary composition.

The remaining concerns identified during Sx1 are intentionally **not**
new Sx1 sprints. They are preserved here as a future backlog for **Sx2
--- Security Evolution / Blackbox**.

Sx2 should begin only when NAV's future architecture makes these threat
surfaces sufficiently real and consequential to justify another
dedicated security campaign.

The existence of a concern in this document does **not** mean it must
automatically become an Sx2 implementation item.

## 2. Locked Future Concerns

### S2-R01 --- Cryptographic Approval Tokens

Current approval uses an in-process mechanism. Future distributed or
higher-trust environments may require cryptographically bound, scoped,
single-use approval tokens.

Potential scope: actor/action/resource binding, replay prevention,
approval transfer prevention, tamper resistance, and remote/distributed
approval.

Trigger: distributed approval, remote execution, or stronger trust
boundaries.

### S2-R02 --- Cryptographic Persistence Integrity

Current SQLite persistence does not provide row-level cryptographic
integrity signatures. Under the current local/in-process threat model
this remains a bounded architectural weakness, not a confirmed
vulnerability.

Potential scope: HMAC/signatures for security-sensitive state, tamper
detection, authenticated persistence records, and integrity verification
during reload/resume.

Trigger: hostile filesystem assumptions, distributed persistence, or
stronger tamper-resistance requirements.

### S2-R03 --- Distributed / Multi-Device Authority

Future NAV manifestations may operate across multiple devices or
processes.

Potential scope: secure authority propagation, identity continuity,
revocation, synchronization, stale-authority prevention, distributed
approval, conflict resolution, and replay resistance.

Trigger: real multi-device execution, remote NAV components, or
distributed capability execution.

### S2-R04 --- Multi-Tenant Isolation

If NAV later supports multiple users, workspaces, or tenants, security
boundaries must prevent cross-tenant state and authority leakage.

Potential scope: tenant-scoped authorization, repository queries,
identity isolation, memory isolation, capability isolation, and
confused-deputy resistance.

Trigger: multi-user / multi-tenant NAV deployment.

### S2-R05 --- Capability Sandboxing

Future third-party or externally sourced capabilities may not be safe to
execute inside the trusted process.

Potential scope: subprocess/container isolation, restricted
filesystem/network access, resource limits, capability trust
classification, and sandbox-escape testing.

Trigger: third-party plugins, untrusted extensions, or externally
supplied capabilities.

### S2-R06 --- Async Execution Races

Future asynchronous/background execution may introduce race conditions
not present in the current single-process model.

Potential scope: optimistic concurrency/versioning, authorization
freshness, approval consumption, duplicate execution prevention, atomic
state transitions, retry races, and concurrent TOCTOU.

Trigger: worker threads, background jobs, task queues, or concurrent
execution.

### S2-R07 --- Network / Remote Exposure

If NAV gains network-facing or remotely accessible interfaces, current
local trust assumptions will no longer be sufficient.

Potential scope: cryptographic authentication, transport security,
remote authorization, session security, replay resistance, request
integrity, abuse resistance, and remote auditability.

Trigger: network APIs, remote clients, or remote capability execution.

### S2-R08 --- Physical Manifestation Security

A future physical NAV manifestation may introduce real-world actuation
and hardware security boundaries.

Potential scope: sensor authorization, actuator authorization, physical
safety interlocks, capability permissions, emergency controls, hardware
trust boundaries, firmware integrity, and physical compromise
assumptions.

> **Having a sensor or actuator does not automatically grant NAV
> permission to use it.**

Trigger: physical NAV manifestation or motors/actuators.

### S2-R09 --- Security Event Durability

The current security event model includes bounded in-memory event
retention.

Potential scope: durable event storage, tamper evidence, event
integrity, retention policies, audit reconstruction, and cross-device
synchronization.

Trigger: stronger audit requirements, distributed operation, or
incident-investigation requirements.

### S2-R10 --- Future Identity / Authentication Evolution

Sx1 validated identity handling and provenance within the current
local/in-process architecture. It intentionally does not treat local
identity sanitization as equivalent to cryptographic authentication.

Potential scope: cryptographic identities, hardware-backed identity,
external authentication, credential lifecycle, key rotation, revocation,
and stronger provenance chains.

Trigger: remote actors, distributed NAV, external users/services, or
hostile execution environments.

## 3. Sx2 Principles

When Sx2 eventually begins:

1.  Do not blindly implement this backlog.
2.  Start with a fresh threat model based on NAV's architecture at that
    time.
3.  Derive actual vulnerability classes from real attack surfaces.
4.  Preserve the distinction between vulnerability, architectural
    weakness, and future risk.
5.  Do not add security complexity merely because a mechanism exists
    elsewhere.
6.  Prefer evidence-backed architectural changes.
7.  Keep stable security contracts/invariants separate from replaceable
    implementations.
8.  Re-test changes adversarially.
9.  Do not reopen Sx1 unless a new finding demonstrates that the
    original closure was invalid.
10. Treat Sx2 as a new security campaign against the future NAV
    architecture.

## 4. Relationship to Normal NAV Development

Sx1 is closed. Normal NAV development continues independently.

These future concerns should not automatically block S26 or later
capability work unless the current implementation directly introduces
one of these threat surfaces.

Security remains a cross-cutting architectural invariant during normal
development.

A future capability that introduces a new security boundary should
address that boundary as part of its own design and testing, while
reserving a dedicated aggregate security campaign for Sx2 when
justified.

## 5. Sx2 Entry Conditions

Sx2 should be considered when major architectural transitions make the
preserved risks materially relevant, such as:

-   distributed NAV
-   multi-device authority
-   network exposure
-   third-party/untrusted plugins
-   asynchronous workers
-   multi-tenant operation
-   physical manifestation with actuation
-   stronger persistence/tamper-resistance requirements
-   external/cryptographic identity
-   materially expanded execution surfaces

The exact trigger should be decided from the architecture and threat
model at that future point.

## 6. Locked Status

**Sx1:** CLOSED 🔒

**Sx2:** Future / not started

**This document:** Preserved backlog and architectural memory for future
security evolution.

No Sx2 sprint is currently active or implied by this document.

*Preserved after Sx1 Blackbox closure.*
