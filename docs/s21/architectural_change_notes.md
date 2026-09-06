# S21 Architectural Change Notes

## Scope of Architectural Additions
S21 establishes the technical foundation for NAV operating across multiple devices and runtimes without premature distributed platform implementation.

### 1. New Contract: `core/contracts/environment.py`
- `EnvironmentIdentity`: Stable identifier for a personal NAV environment (`nav:default` fallback).
- `DevicePlatform`: Enum for host operating systems (`windows`, `linux`, `macos`, `android`, `ios`, `unknown`).
- `DeviceCapabilities`: Descriptive boolean flags for device features (audio in/out, local AI, storage, display, network).
- `DeviceIdentity`: Host-level identifier persisting across runtime process restarts.
- `RuntimeStatus`: Lifecycle state (`starting`, `active`, `detached`, `terminated`).
- `RuntimeIdentity`: Ephemeral process instance descriptor tied to `environment_id` and `device_id`.
- `RuntimeDescriptor`: Combined tuple/dataclass of runtime and host device capabilities.
- `StateOrigin`: State provenance metadata tracking `environment_id`, `origin_runtime_id`, `origin_device_id`, and `state_version`.

### 2. New Core Subsystem: `core/environment/`
- `core/environment/identity.py`: Deterministic UUID generators and platform/architecture detection utilities.
- `core/environment/registry.py`: `RuntimeRegistry` providing runtime lifecycle tracking and validation within an environment.

### 3. Separation of Concerns & Security Alignment
- **Identity vs Authorization**: Environment and Device identities represent *where* execution occurs, strictly separated from `ActorIdentity` (*who* requests it).
- S20 `SecurityService` remains the sole gatekeeper for capability invocation. Environment metadata does not grant bypasses or implicit elevation.
- Local-first architecture is preserved: existing single-runtime execution semantics in Orchestrator and Context remain 100% intact.
