# ADR-001: Voice Retained as Interface Boundary, Not Core Capability

## Status
Accepted

## Context
The S11 brief considered whether Voice should be converted into a `Capability` registered inside `CapabilityRegistry` (like Cognition or Research) to facilitate Avni integration.

## Decision
Voice remains an **Interface Boundary** (`interfaces/voice/`) rather than a `Capability`.
- Voice is an ingress/egress interaction medium that translates between audio signals and NAV standard `Request`/`Response` objects.
- External voice engines (like Avni) will integrate as concrete implementations of `SpeechToText` and `TextToSpeech` provider contracts.

## Consequences
- Preserves the golden invariant: *A voice request is indistinguishable from a text request once it reaches the Orchestrator.*
- Avoids turning the orchestrator into an audio router.
- Avni integrates cleanly via standard STT/TTS adapters.
