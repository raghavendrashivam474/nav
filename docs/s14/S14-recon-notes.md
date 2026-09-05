# S14 Recon Notes — Memory → Context Integration

## Baseline
- v1.3 / 732c7ad
- S12: Context Foundation (PersonalContext in NavContext)
- S13: Memory Intelligence (semantics, lifecycle, contradiction)

## Context Surface (S12)

### ContextManager ABC (`core/context/context_manager.py`)
- `get_context(session_id, user_id, conversation_id) -> NavContext`
- `update_user_context(user_id, **preferences) -> UserContext`
- `update_session_context(session_id, **metadata) -> SessionContext`
- `update_conversation_context(conversation_id, turns_increment, history_summary) -> ConversationContext`
- No personal-context methods on the ABC (S12 kept ABC unchanged)

### DefaultContextManager (`core/context/default_manager.py`)
- Implements ContextManager ABC
- Adds concrete methods: add/remove project/goal/commitment, set_focus
- Uses in-memory ContextStore
- `get_context()` includes `personal_context` from store

### NavContext (`core/contracts/context.py`)
- **Frozen dataclass** — cannot be mutated
- Fields: user, session, conversation, ambient_data, research, personal_context
- `personal_context: PersonalContext | None = None`

### PersonalContext (`core/contracts/context.py`)
- **Frozen dataclass**
- Fields: projects (tuple[Project]), goals (tuple[Goal]), commitments (tuple[Commitment]), current_focus (CurrentFocus | None)
- All explicit (user-declared), no inference

### Relevance dimensions available in PersonalContext:
- `Project.name`, `Project.current_focus`
- `Goal.description`
- `Commitment.description`
- `CurrentFocus.topic`, `CurrentFocus.activity`

## Memory Surface (S13)

### MemoryCapabilityInterface (`core/contracts/memory.py`)
- `store(record) -> bool`
- `retrieve(query) -> list[MemoryRecord]`
- `update(record) -> bool`
- `forget(key) -> bool`
- This ABC lives in **core/contracts/** — safe for core→core dependency

### MemoryQuery (`core/contracts/memory.py`)
- `query_text: str | None`
- `tags: list[str]`
- `limit: int = 10`
- S13 filters: `memory_type`, `min_importance`, `confidence`, `lifecycle_status` (all optional)

### MemoryRecord (`core/contracts/memory.py`)
- **Frozen dataclass**: key, value (Any), tags, metadata (dict)
- Semantics stored as string values in metadata dict

### MemoryService (`capabilities/memory/service.py`)
- Implements MemoryCapabilityInterface
- `supersede(old_key, new_record) -> bool`
- `detect_contradictions(record) -> list[MemoryRecord]`
- `store()` auto-applies semantic defaults via `apply_defaults()`

### S13 Semantics (`capabilities/memory/semantics.py`)
- MemoryType: fact, preference, decision, goal, commitment, observation, instruction, temporary
- Importance: low, normal, high, critical (with IMPORTANCE_RANK)
- Confidence: explicit, inferred, observed, imported, system
- LifecycleStatus: active, superseded, archived
- Meta keys: memory_type, importance, confidence, provenance, lifecycle_status, valid_from, valid_until, superseded_by, supersedes

## Integration Analysis

### Where can Memory safely interact with Context?
- `MemoryCapabilityInterface` in `core/contracts/memory.py` is the natural boundary
- Integration module can live in `core/context/` and depend only on `core/contracts/`
- No need to import from `capabilities/` — semantic values are plain strings in metadata

### Is a new abstraction necessary?
- Yes, but minimal: a `MemoryContextIntegrator` class and `ContextualSnapshot` dataclass
- `NavContext` is frozen, so we need a wrapper that combines base context + relevant memories
- No changes to ContextManager ABC, DefaultContextManager, or any S12/S13 contracts

### Can S14 be implemented without changing existing contracts?
- **Yes.** Zero changes to S12 or S13 code required.
- Only additive: new file `core/context/integration.py`, updated `__init__.py` exports

## Architectural Risk Assessment

| Risk | Assessment | Mitigation |
|------|-----------|------------|
| Coupling | Low — depends only on core contracts | Use MemoryCapabilityInterface ABC |
| Circular dependency | None — core→core only | No capabilities imports |
| API break | None — purely additive | New classes, no modifications |
| Duplicated logic | Minimal — string constants only | Document as S13 value references |
| Persistence problem | None — read-only integration | No writes to memory or context |
| Performance | Low — bounded queries | Limit candidates, cap results |
| Semantic ambiguity | Low — uses S13 metadata directly | Preserve provenance on all items |
