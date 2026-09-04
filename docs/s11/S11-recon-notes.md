# S11 Reconnaissance Notes — Raw Findings

Preserved so future reviewers can trace how the audit was constructed.

---

## Baseline verification (executed)

```text
git branch --show-current  → main
git status                 → clean
git log -1 --oneline       → 2e0e706 docs(s10): add formal post-completion review report
git show v0.10 (tag)       → 2e0e706
git status -uno            → up to date with origin/main
```

> **Note:** Sprint brief cited `bfa4e10` as `v0.10`, but the tag actually points to `2e0e706`. Real `v0.10` is `2e0e706`; `bfa4e10` is the earlier S10 docs commit on `sprint/s10-continuity`.

---

## Files inspected

### Read in full:

- `README.md`
- `pyproject.toml`
- `core/contracts/capability.py`
- `core/contracts/context.py`
- `core/contracts/ai.py`
- `core/contracts/memory.py`
- `core/contracts/research.py`
- `core/contracts/__init__.py` (empty)
- `core/capabilities/registry.py`
- `core/orchestration/orchestrator.py`
- `core/context/__init__.py` (empty)
- `core/log.py`
- `core/__init__.py` (empty)
- `ai/gateway/default_gateway.py`
- `ai/routing/router.py`
- `ai/routing/types.py`
- `capabilities/cognition/cognition.py`
- `capabilities/memory/capability.py`
- `capabilities/research/capability.py`
- `capabilities/research/continuity.py`
- `capabilities/research/context_store.py`
- `capabilities/research/security.py`
- `interfaces/voice/interface.py`
- `interfaces/voice/contracts.py`
- `security/__init__.py` (empty)
- `docs/s10/completion-report.md`
- `docs/s10/architectural_change_notes.md`
- `docs/s10/baseline.md`

### Enumerated:

- Full `ai/` tree
- Full `capabilities/` tree
- Full `interfaces/voice/` tree
- Full `security/` tree
- Full `docs/` tree

---

## Discrepancies between brief and reality

| Brief said | Reality |
| :--- | :--- |
| `v0.10 = bfa4e10` | `v0.10 = 2e0e706`; `bfa4e10` is older |
| `core/registry.py` | `core/capabilities/registry.py` |
| `core/orchestrator.py` | `core/orchestration/orchestrator.py` |
| Voice as capability | Voice as frontend under `interfaces/` |
| Security not built | `security/` package exists but empty; `capabilities/research/security.py` implements per-capability defenses |
| Context system not built | `core/context/` package exists but empty; `ResearchSessionContext` and `NavContext` contracts already defined |
| AI inside core | `ai/` is a top-level sibling of `core/` |

These discrepancies are the reason recon happens before implementation.

---

## Immediate cleanup candidates (verify before touching)

- `ai/router/` vs `ai/routing/` — appears to be a stub leftover
- `core/contracts/__init__.py` — empty, no re-exports

---

*End of recon notes.*
