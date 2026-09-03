# NAV Contract Specifications

## 1. Capability Contract (`core/contracts/capability.py`)
- `Capability`: Base class for all capabilities (`name`, `version`, `description`, `invoke()`).
- `Request`: Immutable payload container (`request_id`, `payload`).
- `Response`: Immutable execution result (`request_id`, `data`, `success`, `error`).

## 2. Memory Contract (`core/contracts/memory.py`)
- `MemoryRecord`: Data model for stored memory items (`key`, `value`, `tags`, `metadata`).
- `MemoryQuery`: Query criteria (`query_text`, `tags`, `limit`).
- `MemoryCapabilityInterface`:
  - `store(record: MemoryRecord) -> bool`
  - `retrieve(query: MemoryQuery) -> list[MemoryRecord]`
  - `update(record: MemoryRecord) -> bool` *(added in S6)*
  - `forget(key: str) -> bool` *(added in S6)*

## 3. AI Gateway Contract (`core/contracts/ai.py`)
- `AIMessage`: Role and content representation.
- `AIRequest`: Message list, temperature, options (including routing hints).
- `AIResponse`: Output content, model used, token usage.
- `AIGateway`: Provider-agnostic generation protocol.

## 4. Voice Contract (`interfaces/voice/contracts.py`)
- `AudioInput`, `AudioOutput`
- `SpeechToText`, `TextToSpeech`
