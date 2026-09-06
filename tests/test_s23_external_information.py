"""
NAV v2 — S23: External Information Capability Tests.

Covers:
- Contract validation (§19: Contract tests)
- Provider behavior (§19: Provider tests)
- Capability integration (§19: Capability integration tests)
- Security boundary (§19: Security tests — structural)
- Honesty invariants (§16: No fake research)
- Live Wikipedia integration (§23.1: Actual network boundary)
- Orchestrator capability dispatch (§23.1: Interface matching)
"""

from __future__ import annotations

from typing import Any

import pytest

from capabilities.external_information.capability import (
    ExternalInformationCapability,
)
from capabilities.external_information.registry import ProviderRegistry
from capabilities.external_information.static_provider import (
    StaticInformationProvider,
)
from capabilities.external_information.wikipedia_provider import WikipediaProvider
from core.contracts.external_information import (
    ExternalInformationItem,
    ExternalInformationRequest,
    ExternalInformationResult,
    RetrievalStatus,
    SourceMetadata,
)

# ===================================================================
# CONTRACT TESTS
# ===================================================================


class TestExternalInformationRequest:
    """S23 §19: Contract tests — request construction."""

    def test_valid_request(self) -> None:
        req = ExternalInformationRequest(query="What is NAV?")
        assert req.query == "What is NAV?"
        assert req.result_limit == 5
        assert req.freshness_seconds is None

    def test_empty_query_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            ExternalInformationRequest(query="")

    def test_whitespace_query_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            ExternalInformationRequest(query="   ")

    def test_invalid_result_limit(self) -> None:
        with pytest.raises(ValueError, match="result_limit"):
            ExternalInformationRequest(query="test", result_limit=0)

    def test_negative_freshness_rejected(self) -> None:
        with pytest.raises(ValueError, match="freshness_seconds"):
            ExternalInformationRequest(query="test", freshness_seconds=-1)

    def test_frozen_dataclass(self) -> None:
        req = ExternalInformationRequest(query="test")
        with pytest.raises(AttributeError):
            req.query = "changed"  # type: ignore[misc]


class TestExternalInformationResult:
    """S23 §19: Contract tests — result structure."""

    def _make_source(self) -> SourceMetadata:
        return SourceMetadata(
            source_name="Test Source",
            provider_id="test-provider",
        )

    def test_success_with_items(self) -> None:
        item = ExternalInformationItem(
            content="Found it.",
            source=self._make_source(),
        )
        result = ExternalInformationResult(
            status=RetrievalStatus.SUCCESS,
            items=[item],
            provider_id="test-provider",
        )
        assert result.is_success
        assert result.has_items
        result.assert_honest()  # Should not raise

    def test_no_results_is_honest(self) -> None:
        result = ExternalInformationResult(
            status=RetrievalStatus.NO_RESULTS,
            items=[],
            provider_id="test-provider",
        )
        assert not result.is_success
        assert not result.has_items
        result.assert_honest()  # Should not raise

    def test_failure_with_items_is_dishonest(self) -> None:
        """S23 §16: Non-success status must not carry items."""
        item = ExternalInformationItem(
            content="Should not be here.",
            source=self._make_source(),
        )
        result = ExternalInformationResult(
            status=RetrievalStatus.PROVIDER_ERROR,
            items=[item],
            provider_id="test-provider",
        )
        with pytest.raises(ValueError, match="Integrity violation"):
            result.assert_honest()

    def test_success_without_items_is_dishonest(self) -> None:
        """S23 §16: SUCCESS with no items should be NO_RESULTS."""
        result = ExternalInformationResult(
            status=RetrievalStatus.SUCCESS,
            items=[],
            provider_id="test-provider",
        )
        with pytest.raises(ValueError, match="Integrity violation"):
            result.assert_honest()


# ===================================================================
# PROVIDER TESTS
# ===================================================================


class TestStaticProvider:
    """S23 §19: Provider tests."""

    def setup_method(self) -> None:
        self.provider = StaticInformationProvider()

    def test_provider_id(self) -> None:
        assert self.provider.provider_id == "static-provider-v1"

    def test_is_available(self) -> None:
        assert self.provider.is_available() is True

    def test_known_query_returns_success(self) -> None:
        req = ExternalInformationRequest(query="What is the NAV version?")
        result = self.provider.retrieve(req)
        assert result.status == RetrievalStatus.SUCCESS
        assert result.has_items
        assert "NAV v2" in result.items[0].content

    def test_unknown_query_returns_no_results(self) -> None:
        req = ExternalInformationRequest(query="What is the weather on Mars?")
        result = self.provider.retrieve(req)
        assert result.status == RetrievalStatus.NO_RESULTS
        assert not result.has_items

    def test_result_includes_provenance(self) -> None:
        """S23 §17: Acquisition-time metadata must be present."""
        req = ExternalInformationRequest(query="S23 status")
        result = self.provider.retrieve(req)
        assert result.status == RetrievalStatus.SUCCESS
        item = result.items[0]
        assert item.source.provider_id == "static-provider-v1"
        assert item.source.source_name == "Static Knowledge Base"
        assert item.source.retrieved_at is not None
        assert item.source.query_echo == "S23 status"

    def test_custom_known_responses(self) -> None:
        provider = StaticInformationProvider(known_responses={"hello": "world"})
        req = ExternalInformationRequest(query="say hello")
        result = provider.retrieve(req)
        assert result.status == RetrievalStatus.SUCCESS
        assert result.items[0].content == "world"


# ===================================================================
# REGISTRY TESTS
# ===================================================================


class TestProviderRegistry:
    """Provider registry behavior."""

    def test_register_and_retrieve(self) -> None:
        registry = ProviderRegistry()
        provider = StaticInformationProvider()
        registry.register(provider, set_default=True)
        assert registry.get_provider() is provider

    def test_duplicate_registration_rejected(self) -> None:
        registry = ProviderRegistry()
        provider = StaticInformationProvider()
        registry.register(provider)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(provider)

    def test_no_providers_raises(self) -> None:
        registry = ProviderRegistry()
        with pytest.raises(RuntimeError, match="No external"):
            registry.get_provider()

    def test_unknown_provider_raises(self) -> None:
        registry = ProviderRegistry()
        registry.register(StaticInformationProvider())
        with pytest.raises(ValueError, match="Unknown provider"):
            registry.get_provider("nonexistent")


# ===================================================================
# CAPABILITY INTEGRATION TESTS
# ===================================================================


class TestExternalInformationCapability:
    """S23 §19: Capability integration tests."""

    def setup_method(self) -> None:
        self.registry = ProviderRegistry()
        self.registry.register(StaticInformationProvider(), set_default=True)
        self.capability = ExternalInformationCapability(self.registry)

    def test_successful_acquisition(self) -> None:
        """Full path: request → capability → provider → result."""
        req = ExternalInformationRequest(query="NAV version info")
        result = self.capability.acquire(req)
        assert result.status == RetrievalStatus.SUCCESS
        assert result.has_items
        assert result.provider_id == "static-provider-v1"

    def test_no_results_acquisition(self) -> None:
        req = ExternalInformationRequest(query="something completely unknown")
        result = self.capability.acquire(req)
        assert result.status == RetrievalStatus.NO_RESULTS
        assert not result.has_items

    def test_empty_query_returns_invalid(self) -> None:
        req = ExternalInformationRequest(query="x")
        # Manually bypass the constructor validation for this test
        object.__setattr__(req, "query", "   ")
        result = self.capability.acquire(req)
        assert result.status == RetrievalStatus.INVALID_REQUEST

    def test_unavailable_provider(self) -> None:
        """S23 §15: UNAVAILABLE must be explicit."""
        empty_registry = ProviderRegistry()
        cap = ExternalInformationCapability(empty_registry)
        req = ExternalInformationRequest(query="test")
        result = cap.acquire(req)
        assert result.status == RetrievalStatus.UNAVAILABLE

    def test_provenance_preserved_through_capability(self) -> None:
        """S23 §17: Metadata survives the full pipeline."""
        req = ExternalInformationRequest(
            query="S23 status",
            request_id="test-req-001",
        )
        result = self.capability.acquire(req)
        assert result.request_id == "test-req-001"
        assert result.items[0].source.query_echo == "S23 status"


# ===================================================================
# SECURITY STRUCTURAL TESTS
# ===================================================================


class TestSecurityBoundary:
    """
    S23 §14 / §19: Security tests.

    NOTE: Full S20 integration tests require the existing security
    plane to be wired. These tests verify structural invariants:
    - The capability does NOT contain its own authorization logic
    - The capability assumes authorization has already occurred
    """

    def test_capability_has_no_authorize_method(self) -> None:
        """The capability must not define its own auth."""
        cap = ExternalInformationCapability(ProviderRegistry())
        assert not hasattr(cap, "authorize")
        assert not hasattr(cap, "is_allowed")
        assert not hasattr(cap, "check_permission")

    def test_capability_has_no_security_imports(self) -> None:
        """
        Structural check: capability module should not import
        security internals. Authorization happens upstream.
        """
        import capabilities.external_information.capability as cap_mod

        source = open(cap_mod.__file__).read()
        assert "from core.security" not in source
        assert "authorize(" not in source
        assert "is_allowed(" not in source


# ===================================================================
# LIVE WIKIPEDIA INTEGRATION & ORCHESTRATOR DISPATCH TESTS (S23.1)
# ===================================================================


class TestLiveWikipediaProvider:
    """S23.1: Actual network boundary tests using Wikipedia API."""

    def setup_method(self) -> None:
        self.provider = WikipediaProvider()

    def test_live_retrieval_success(self) -> None:
        """Verifies real internet lookup & provenance parsing."""
        if not self.provider.is_available():
            pytest.skip("Wikipedia API endpoint is currently unreachable (offline).")

        req = ExternalInformationRequest(query="Artificial Intelligence", result_limit=2)
        result = self.provider.retrieve(req)

        # Integrity Validation
        assert result.status == RetrievalStatus.SUCCESS
        assert len(result.items) > 0
        assert result.provider_id == "wikipedia-api-provider"

        # Provenance Validation
        item = result.items[0]
        assert "Wikipedia: " in item.source.source_name
        assert "wikipedia" in item.source.source_url.lower()
        assert item.source.retrieved_at is not None
        assert item.source.query_echo == "Artificial Intelligence"

    def test_live_retrieval_no_results(self) -> None:
        """Ensures non-existent query yields clean NO_RESULTS status."""
        if not self.provider.is_available():
            pytest.skip("Wikipedia API endpoint is currently unreachable (offline).")

        req = ExternalInformationRequest(query="xyzqwerewt12349876", result_limit=1)
        result = self.provider.retrieve(req)

        assert result.status == RetrievalStatus.NO_RESULTS
        assert len(result.items) == 0


class TestOrchestratorCapabilityDispatch:
    """
    S23.1: Validates that capability matches Orchestrator registration
    and dispatch signature without modifying Orchestrator semantics.
    """

    class MockOrchestrator:
        """Represents the actual core/orchestration/orchestrator.py signature."""

        def __init__(self) -> None:
            self._capabilities: dict[str, Any] = {}

        def register_capability(self, name: str, capability: Any) -> None:
            self._capabilities[name] = capability

        def execute_action(
            self, actor_id: str, capability_name: str, action_data: dict[str, Any]
        ) -> dict[str, Any]:
            cap = self._capabilities.get(capability_name)
            if not cap:
                raise ValueError("Capability not registered")
            return cap.execute(action_data)

    def test_end_to_end_orchestration_dispatch_with_static_provider(self) -> None:
        # 1. Initialize Registry and Capability
        registry = ProviderRegistry()
        registry.register(StaticInformationProvider(), set_default=True)
        capability = ExternalInformationCapability(registry)

        # 2. Register to Orchestrator
        orchestrator = self.MockOrchestrator()
        orchestrator.register_capability("external_information", capability)

        # 3. Simulate Orchestrator Action Dispatch
        action_packet = {
            "query": "S23 status",
            "result_limit": 1,
            "request_id": "orchestrator-req-101",
        }

        response = orchestrator.execute_action("user-001", "external_information", action_packet)

        # 4. Verify Dispatch output maps to S23 Core contracts
        assert response["status"] == RetrievalStatus.SUCCESS.value
        assert response["provider_id"] == "static-provider-v1"
        assert response["request_id"] == "orchestrator-req-101"
        assert len(response["items"]) == 1

        content_match = "S23 implements the External Information Capability"
        assert content_match in response["items"][0]["content"]
