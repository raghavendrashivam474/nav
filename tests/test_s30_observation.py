"""
NAV v2 — S30: Observation Tests.

Covers contracts, engine, service, and capability layers.
"""

from __future__ import annotations

import pytest

from capabilities.observation.capability import ObservationCapability
from capabilities.observation.engine import ObservationEngine
from capabilities.observation.service import ObservationService
from core.contracts.capability import Request
from core.contracts.observation import (
    Observation,
    ObservationRequest,
    ObservationResult,
    ObservationSource,
    ObservationState,
)

# ======================================================================
# Contract Tests
# ======================================================================


class TestObservationRequestContract:
    def test_valid_creation(self) -> None:
        req = ObservationRequest(
            subject="test-resource",
            source=ObservationSource.DIRECT_INSPECTION,
        )
        assert req.subject == "test-resource"
        assert req.source == ObservationSource.DIRECT_INSPECTION
        assert req.action_id is None

    def test_parameters_frozen(self) -> None:
        req = ObservationRequest(
            subject="t",
            source=ObservationSource.LOCAL_STATE,
            parameters={"key": "value"},
        )
        with pytest.raises(TypeError):
            req.parameters["new"] = "val"  # type: ignore[index]

    def test_metadata_frozen(self) -> None:
        req = ObservationRequest(
            subject="t",
            source=ObservationSource.LOCAL_STATE,
            metadata={"k": "v"},
        )
        with pytest.raises(TypeError):
            req.metadata["new"] = "val"  # type: ignore[index]

    def test_empty_subject_rejected(self) -> None:
        with pytest.raises(ValueError, match="subject must not be empty"):
            ObservationRequest(
                subject="",
                source=ObservationSource.DIRECT_INSPECTION,
            )

    def test_whitespace_subject_rejected(self) -> None:
        with pytest.raises(ValueError, match="subject must not be empty"):
            ObservationRequest(
                subject="   ",
                source=ObservationSource.DIRECT_INSPECTION,
            )

    def test_action_id_optional(self) -> None:
        req = ObservationRequest(
            subject="s",
            source=ObservationSource.ACTION_RESULT,
            action_id="a-123",
        )
        assert req.action_id == "a-123"

    def test_action_id_none_by_default(self) -> None:
        req = ObservationRequest(
            subject="s",
            source=ObservationSource.DIRECT_INSPECTION,
        )
        assert req.action_id is None


class TestObservationContract:
    def test_valid_creation(self) -> None:
        from datetime import datetime, timezone

        obs = Observation(
            observation_id="o-1",
            source=ObservationSource.DIRECT_INSPECTION,
            subject="file-x",
            observed_state="file exists",
            state=ObservationState.OBSERVED,
            observed_at=datetime.now(timezone.utc),
        )
        assert obs.state == ObservationState.OBSERVED
        assert obs.observed_state == "file exists"

    def test_empty_observation_id_rejected(self) -> None:
        from datetime import datetime, timezone

        with pytest.raises(ValueError, match="observation_id must not be empty"):
            Observation(
                observation_id="",
                source=ObservationSource.DIRECT_INSPECTION,
                subject="s",
                observed_state="x",
                state=ObservationState.OBSERVED,
                observed_at=datetime.now(timezone.utc),
            )

    def test_empty_observed_state_rejected(self) -> None:
        from datetime import datetime, timezone

        with pytest.raises(ValueError, match="observed_state must not be empty"):
            Observation(
                observation_id="o-1",
                source=ObservationSource.DIRECT_INSPECTION,
                subject="s",
                observed_state="",
                state=ObservationState.OBSERVED,
                observed_at=datetime.now(timezone.utc),
            )

    def test_metadata_frozen(self) -> None:
        from datetime import datetime, timezone

        obs = Observation(
            observation_id="o-1",
            source=ObservationSource.LOCAL_STATE,
            subject="s",
            observed_state="x",
            state=ObservationState.OBSERVED,
            observed_at=datetime.now(timezone.utc),
            metadata={"k": "v"},
        )
        with pytest.raises(TypeError):
            obs.metadata["new"] = "val"  # type: ignore[index]

    def test_unknown_state_preserved(self) -> None:
        from datetime import datetime, timezone

        obs = Observation(
            observation_id="o-2",
            source=ObservationSource.EXTERNAL_REPORT,
            subject="remote-api",
            observed_state="connection timed out",
            state=ObservationState.UNKNOWN,
            observed_at=datetime.now(timezone.utc),
        )
        assert obs.state == ObservationState.UNKNOWN

    def test_conflicting_state_preserved(self) -> None:
        from datetime import datetime, timezone

        obs = Observation(
            observation_id="o-3",
            source=ObservationSource.DIRECT_INSPECTION,
            subject="file-x",
            observed_state="conflicting reports about file existence",
            state=ObservationState.CONFLICTING,
            observed_at=datetime.now(timezone.utc),
        )
        assert obs.state == ObservationState.CONFLICTING


class TestObservationResultContract:
    def test_valid_creation(self) -> None:
        result = ObservationResult(
            observation_id="o-1",
            subject="s",
            state=ObservationState.OBSERVED,
            message="Observation completed.",
        )
        assert result.state == ObservationState.OBSERVED
        assert result.observation is None

    def test_empty_message_rejected(self) -> None:
        with pytest.raises(ValueError, match="message must not be empty"):
            ObservationResult(
                observation_id="o-1",
                subject="s",
                state=ObservationState.OBSERVED,
                message="",
            )

    def test_invalid_state_no_observation(self) -> None:
        result = ObservationResult(
            observation_id="o-1",
            subject="s",
            state=ObservationState.INVALID,
            observation=None,
            message="Validation failed.",
        )
        assert result.observation is None


# ======================================================================
# Engine Tests
# ======================================================================


class TestObservationEngine:
    def test_echo_observation_with_expected_state(self) -> None:
        engine = ObservationEngine()
        req = ObservationRequest(
            subject="test-target",
            source=ObservationSource.DIRECT_INSPECTION,
            parameters={"expected_state": "file exists"},
        )
        result = engine.observe(req)
        assert result.state == ObservationState.OBSERVED
        assert result.observation is not None
        assert result.observation.observed_state == "file exists"
        assert result.observation.provenance == "echo:direct_inspection"

    def test_echo_observation_without_expected_state(self) -> None:
        engine = ObservationEngine()
        req = ObservationRequest(
            subject="test-target",
            source=ObservationSource.DIRECT_INSPECTION,
        )
        result = engine.observe(req)
        assert result.state == ObservationState.UNKNOWN
        assert result.observation is not None

    def test_state_check_found(self) -> None:
        registry = {"file-x": "exists", "file-y": "deleted"}
        engine = ObservationEngine(state_registry=registry)
        req = ObservationRequest(
            subject="file-x",
            source=ObservationSource.LOCAL_STATE,
        )
        result = engine.observe(req)
        assert result.state == ObservationState.OBSERVED
        assert result.observation is not None
        assert result.observation.observed_state == "exists"

    def test_state_check_not_found(self) -> None:
        registry = {"file-x": "exists"}
        engine = ObservationEngine(state_registry=registry)
        req = ObservationRequest(
            subject="file-z",
            source=ObservationSource.LOCAL_STATE,
        )
        result = engine.observe(req)
        assert result.state == ObservationState.NOT_OBSERVED
        assert result.observation is not None

    def test_no_adapter_returns_unknown(self) -> None:
        engine = ObservationEngine()
        req = ObservationRequest(
            subject="remote-api",
            source=ObservationSource.EXTERNAL_REPORT,
        )
        result = engine.observe(req)
        assert result.state == ObservationState.UNKNOWN
        assert result.observation is not None
        assert "no observation adapter" in result.observation.observed_state

    def test_action_id_linkage(self) -> None:
        engine = ObservationEngine()
        req = ObservationRequest(
            subject="test-target",
            source=ObservationSource.DIRECT_INSPECTION,
            action_id="a-123",
            parameters={"expected_state": "created"},
        )
        result = engine.observe(req)
        assert result.observation is not None
        assert result.observation.action_id == "a-123"

    def test_unknown_source_returns_unknown(self) -> None:
        engine = ObservationEngine()
        req = ObservationRequest(
            subject="mystery",
            source=ObservationSource.UNKNOWN,
        )
        result = engine.observe(req)
        assert result.state == ObservationState.UNKNOWN

    def test_deterministic_behavior(self) -> None:
        """Same input produces same state (IDs differ, states match)."""
        engine = ObservationEngine()
        req = ObservationRequest(
            subject="t",
            source=ObservationSource.DIRECT_INSPECTION,
            parameters={"expected_state": "ok"},
        )
        r1 = engine.observe(req)
        r2 = engine.observe(req)
        assert r1.state == r2.state
        assert r1.observation_id != r2.observation_id


# ======================================================================
# Service Tests
# ======================================================================


class TestObservationService:
    def test_observe_delegates_to_engine(self) -> None:
        service = ObservationService()
        req = ObservationRequest(
            subject="t",
            source=ObservationSource.DIRECT_INSPECTION,
            parameters={"expected_state": "present"},
        )
        result = service.observe(req)
        assert result.state == ObservationState.OBSERVED

    def test_service_with_state_registry(self) -> None:
        registry = {"db-row-1": "active"}
        service = ObservationService(state_registry=registry)
        req = ObservationRequest(
            subject="db-row-1",
            source=ObservationSource.LOCAL_STATE,
        )
        result = service.observe(req)
        assert result.state == ObservationState.OBSERVED
        assert result.observation is not None
        assert result.observation.observed_state == "active"


# ======================================================================
# Capability Tests
# ======================================================================


class TestObservationCapability:
    def test_valid_observe(self) -> None:
        cap = ObservationCapability()
        req = Request(
            request_id="r-1",
            payload={
                "action": "observe",
                "subject": "test-file",
                "source": "direct_inspection",
                "parameters": {"expected_state": "exists"},
            },
        )
        resp = cap.invoke(req)
        assert resp.success is True
        assert resp.data["state"] == "observed"
        assert resp.data["observation"]["observed_state"] == "exists"

    def test_missing_subject(self) -> None:
        cap = ObservationCapability()
        req = Request(
            request_id="r-2",
            payload={
                "action": "observe",
                "subject": "",
                "source": "direct_inspection",
            },
        )
        resp = cap.invoke(req)
        assert resp.success is False
        assert "subject" in resp.error.lower()

    def test_missing_source(self) -> None:
        cap = ObservationCapability()
        req = Request(
            request_id="r-3",
            payload={
                "action": "observe",
                "subject": "x",
                "source": "",
            },
        )
        resp = cap.invoke(req)
        assert resp.success is False

    def test_unsupported_source(self) -> None:
        cap = ObservationCapability()
        req = Request(
            request_id="r-4",
            payload={
                "action": "observe",
                "subject": "x",
                "source": "telepathy",
            },
        )
        resp = cap.invoke(req)
        assert resp.success is False
        assert "unsupported" in resp.error.lower()

    def test_unknown_action(self) -> None:
        cap = ObservationCapability()
        req = Request(
            request_id="r-5",
            payload={"action": "predict"},
        )
        resp = cap.invoke(req)
        assert resp.success is False

    def test_capability_metadata(self) -> None:
        cap = ObservationCapability()
        assert cap.name == "observation"
        assert cap.version == "1.0.0"


# ======================================================================
# Conflict & Unknown Semantics
# ======================================================================


class TestObservationSemantics:
    def test_not_observed_distinct_from_unknown(self) -> None:
        """NOT_OBSERVED means 'looked and confirmed absent'.
        UNKNOWN means 'could not determine'."""
        registry: dict[str, str] = {}
        engine = ObservationEngine(state_registry=registry)

        # NOT_OBSERVED: looked, not there
        req1 = ObservationRequest(
            subject="missing-file",
            source=ObservationSource.LOCAL_STATE,
        )
        r1 = engine.observe(req1)
        assert r1.state == ObservationState.NOT_OBSERVED

        # UNKNOWN: no adapter for this source
        req2 = ObservationRequest(
            subject="missing-file",
            source=ObservationSource.EXTERNAL_REPORT,
        )
        r2 = engine.observe(req2)
        assert r2.state == ObservationState.UNKNOWN

        assert r1.state != r2.state

    def test_conflicting_observations_preserved(self) -> None:
        """Two observations that disagree are both preserved."""
        from datetime import datetime, timezone

        obs_a = Observation(
            observation_id="o-a",
            source=ObservationSource.DIRECT_INSPECTION,
            subject="file-x",
            observed_state="file exists",
            state=ObservationState.OBSERVED,
            observed_at=datetime.now(timezone.utc),
        )
        obs_b = Observation(
            observation_id="o-b",
            source=ObservationSource.EXTERNAL_REPORT,
            subject="file-x",
            observed_state="file does not exist",
            state=ObservationState.OBSERVED,
            observed_at=datetime.now(timezone.utc),
        )
        # Both exist independently — no silent overwrite
        assert obs_a.observed_state != obs_b.observed_state
        assert obs_a.observation_id != obs_b.observation_id

    def test_observation_does_not_inflate_semantics(self) -> None:
        """Echo adapter returns exactly what was provided."""
        engine = ObservationEngine()
        req = ObservationRequest(
            subject="api-endpoint",
            source=ObservationSource.DIRECT_INSPECTION,
            parameters={"expected_state": "HTTP 200 received"},
        )
        result = engine.observe(req)
        assert result.observation is not None
        # Must NOT inflate to "operation definitely completed"
        assert result.observation.observed_state == "HTTP 200 received"
