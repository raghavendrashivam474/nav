# Sx1.4 Speculative Attacks & Future Threat Vectors

## 1. Physical Actuation Bypass (Future Embodiment)
- **Threat**: When physical actuators (arms, motors, speakers, cameras) are integrated, direct invocation of hardware drivers could bypass security policies.
- **Recommendation**: Hardware drivers must only be accessible via registered Capability adapters managed by the Orchestrator.

## 2. Multi-Tenant RPC / Remote Service Exposure
- **Threat**: If NAV services are exposed over gRPC/REST without Orchestrator mediation, external callers could reach `WorkService` directly.
- **Recommendation**: Service APIs must never be bound to network interfaces; only the Orchestrator API endpoint should be exposed over the network.
