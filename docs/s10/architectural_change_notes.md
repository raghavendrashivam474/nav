# S10 Architectural Change Note: Research Continuity & Session Context

## Observed Problem
In v0.9 (S9), every research invocation is isolated and stateless. When a user conducts research on topic X and follows up with "Go deeper", "Focus on manufacturing", or "What sources support this?", NAV treats each request as an isolated question without awareness of the active investigation. Conversely, automatically storing all research raw data into long-term memory causes memory pollution.

## Evidence
S9 validation scenarios confirmed that while single-turn research is sound, multi-turn follow-ups require manual re-specification of the topic and scope by the user. S9 completion report explicitly identified continuity as the primary missing bridge toward a personal system.

## Existing Components Responsible
- `core/contracts/research.py`: Defines `ResearchQuery` and `ResearchResult`.
- `core/contracts/context.py`: Defines minimal `SessionContext` and `ConversationContext`.
- `capabilities/research/service.py`: Executes single-turn research.
- `capabilities/research/capability.py`: Invokes research for Orchestrator.

## Why Current Implementation is Insufficient
- `ResearchQuery` lacks explicit linkage to prior session/investigation state.
- There is no contract or service component to resolve relative follow-ups ("go deeper", "focus on X") against prior investigation history.
- Context contracts in `core/contracts/context.py` are stub dataclasses without research session specialization.

## Smallest Viable Change
1. Extend `core/contracts/context.py` to add `ResearchContext` data model preserving 100% backward compatibility with default arguments.
2. Implement `capabilities/research/continuity.py` (`ResearchContinuityResolver` & `ResearchSession`) which inspects an incoming prompt against the active `ResearchContext` to determine follow-up intent (`NEW`, `DEEPEN`, `FOCUS`, `PROVENANCE`) and constructs a refined `ResearchQuery`.
3. Support session tracking in `ResearchCapability` and `CognitionCapability` so multi-turn sessions can pass and update session tokens without touching the database or polluting long-term memory.

## Alternatives Considered
- *Alternative A: Dump all research findings automatically into SQLite Memory.*
  - **Rejected**: Violates the principle of memory isolation (brief §6 & §11). Research is volatile session context; Memory is for durable, explicit user knowledge.
- *Alternative B: Rewrite Orchestrator to be stateful.*
  - **Rejected**: Violates Core protection rule. Orchestrator remains a stateless, clean request router. State is carried via context/payloads or session-level interfaces.

## Affected Contracts
- `core/contracts/context.py`: Add `ResearchContext` data model.
- `core/contracts/research.py`: Minor continuation metadata helper if needed, no breaking changes.

## Backward Compatibility
100% preserved. All existing tests passing in v0.9 will continue to pass because default behavior for single-turn queries without context remains unchanged.

## Testing Impact
Unit tests for `ResearchContinuityResolver`, integration tests for multi-turn scenarios (A, B, C, D), and regression suite.
