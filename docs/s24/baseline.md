# S24 Baseline

## Starting Point

- **NAV Version:** v2.0
- **Commit:** a8ecd9f
- **Branch:** main (clean, synced with origin/main)

## S23 External Information Capability (Operational)

### Contracts (`core/contracts/external_information.py`)
- `RetrievalStatus` — 7-state enum (SUCCESS, NO_RESULTS, PROVIDER_ERROR,
  TIMEOUT, INVALID_REQUEST, UNAVAILABLE, UNAUTHORIZED)
- `ExternalInformationRequest` — frozen, validated query + constraints
- `SourceMetadata` — frozen, acquisition-time provenance (source_name,
  source_url, provider_id, retrieved_at, query_echo)
- `ExternalInformationItem` — frozen, content + SourceMetadata + relevance
- `ExternalInformationResult` — frozen, status + items + assert_honest()

### Providers (`capabilities/external_information/`)
- `StaticInformationProvider` — deterministic, pre-configured responses
- `WikipediaProvider` — live Wikipedia search API
- `ProviderRegistry` — provider lifecycle and selection
- `ExternalInformationCapability` — Orchestrator integration point

### Tests
- `tests/test_s23_external_information.py` — 25 tests, all passing

## Frozen Systems (Not Modified by S24)

| Sprint | System | Status |
|--------|--------|--------|
| S17 | Work | Frozen |
| S18 | Human Control | Frozen |
| S19 | Interaction | Frozen |
| S20 | Security | Frozen |
| S21 | Environment | Frozen |
| S22 | Integration | Frozen |
| S23 | External Information | Frozen |
| — | Orchestrator | Frozen |
| — | Memory | Frozen |
| — | Context | Frozen |

## Pre-S24 Test Baseline

- Total tests: 648 (excluding optional pypdf dependency)
- Status: All passing
- S24 adds: 49 new tests
