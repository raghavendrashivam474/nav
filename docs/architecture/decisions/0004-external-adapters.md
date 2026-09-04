# ADR-004: External System Integration via Adapter/Provider Pattern

## Status
Accepted

## Context
Need a clear architectural policy for integrating independent systems (specifically Avni) without repository entanglement.

## Decision
All external systems must integrate as Adapters behind NAV abstract contracts (`AIGateway`, `SpeechToText`, `TextToSpeech`, `SearchProvider`).
External code is never imported into NAV Core.

## Consequences
- Strict decoupling: changes to Avni internal representations or models do not break NAV.
- Transport choice (HTTP/gRPC/IPC) is encapsulated within adapters.
