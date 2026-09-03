"""Unit tests for the S5 Hybrid AI Layer / Model Router.

All tests use fake providers and metadata — no live API calls required.
Tests cover: routing decisions, constraint enforcement, fallback behaviour,
privacy protection, configuration, and backward compatibility.
"""

from __future__ import annotations

import unittest
from typing import TYPE_CHECKING

from ai.errors import RoutingError
from ai.routing.router import ModelRouter
from ai.routing.types import (
    CostClass,
    Locality,
    ProviderMetadata,
    QualityClass,
    RoutingContext,
)
from core.contracts.ai import AIMessage, AIRequest, AIResponse

if TYPE_CHECKING:
    from ai.gateway.default_gateway import DefaultAIGateway


# ------------------------------------------------------------------
# Test helpers
# ------------------------------------------------------------------


def _make_registry(*names: str) -> dict[str, ProviderMetadata]:
    """Build a test provider registry from shorthand names."""
    presets: dict[str, ProviderMetadata] = {
        "ollama": ProviderMetadata(
            name="ollama",
            locality=Locality.LOCAL,
            cost_class=CostClass.FREE,
            quality_class=QualityClass.STANDARD,
        ),
        "openai": ProviderMetadata(
            name="openai",
            locality=Locality.REMOTE,
            cost_class=CostClass.PAID,
            quality_class=QualityClass.HIGH,
        ),
        "free_remote": ProviderMetadata(
            name="free_remote",
            locality=Locality.REMOTE,
            cost_class=CostClass.FREE,
            quality_class=QualityClass.STANDARD,
        ),
        "local_strong": ProviderMetadata(
            name="local_strong",
            locality=Locality.LOCAL,
            cost_class=CostClass.FREE,
            quality_class=QualityClass.HIGH,
        ),
        "unavailable": ProviderMetadata(
            name="unavailable",
            locality=Locality.LOCAL,
            cost_class=CostClass.FREE,
            quality_class=QualityClass.STANDARD,
            available=False,
        ),
    }
    return {n: presets[n] for n in names if n in presets}


# ------------------------------------------------------------------
# Routing decision tests
# ------------------------------------------------------------------


class TestRoutingBasic(unittest.TestCase):
    """Basic routing decisions with default context."""

    def setUp(self) -> None:
        self.registry = _make_registry("ollama", "openai")
        self.router = ModelRouter(self.registry)

    def test_default_context_selects_a_provider(self) -> None:
        ctx = RoutingContext()
        decision = self.router.route(ctx)
        self.assertIn(decision.provider_name, ("ollama", "openai"))

    def test_default_context_includes_fallback(self) -> None:
        ctx = RoutingContext()
        decision = self.router.route(ctx)
        # The non-selected provider should be in the fallback chain
        all_providers = {decision.provider_name, *decision.fallback_chain}
        self.assertEqual(all_providers, {"ollama", "openai"})


class TestRoutingPrivacy(unittest.TestCase):
    """Privacy constraint enforcement."""

    def setUp(self) -> None:
        self.registry = _make_registry("ollama", "openai")
        self.router = ModelRouter(self.registry)

    def test_local_only_selects_local_provider(self) -> None:
        ctx = RoutingContext(privacy="local_only")
        decision = self.router.route(ctx)
        self.assertEqual(decision.provider_name, "ollama")

    def test_local_only_excludes_remote_from_fallback(self) -> None:
        ctx = RoutingContext(privacy="local_only")
        decision = self.router.route(ctx)
        self.assertNotIn("openai", decision.fallback_chain)

    def test_local_only_with_no_local_provider_raises(self) -> None:
        registry = _make_registry("openai")  # only remote
        router = ModelRouter(registry)
        ctx = RoutingContext(privacy="local_only")
        with self.assertRaises(RoutingError):
            router.route(ctx)

    def test_explicit_local_only_constraint(self) -> None:
        ctx = RoutingContext(constraints=("local_only",))
        decision = self.router.route(ctx)
        self.assertEqual(decision.provider_name, "ollama")
        self.assertNotIn("openai", decision.fallback_chain)


class TestRoutingQuality(unittest.TestCase):
    """Quality preference routing."""

    def setUp(self) -> None:
        self.registry = _make_registry("ollama", "openai")
        self.router = ModelRouter(self.registry)

    def test_high_quality_prefers_stronger_provider(self) -> None:
        ctx = RoutingContext(quality_requirement="high")
        decision = self.router.route(ctx)
        self.assertEqual(decision.provider_name, "openai")

    def test_high_quality_with_local_only_stays_local(self) -> None:
        """Hard constraint (privacy) overrides soft preference (quality)."""
        ctx = RoutingContext(
            quality_requirement="high",
            privacy="local_only",
        )
        decision = self.router.route(ctx)
        self.assertEqual(decision.provider_name, "ollama")

    def test_high_quality_with_local_strong_available(self) -> None:
        registry = _make_registry("ollama", "openai", "local_strong")
        router = ModelRouter(registry)
        ctx = RoutingContext(
            quality_requirement="high",
            privacy="local_only",
        )
        decision = router.route(ctx)
        self.assertEqual(decision.provider_name, "local_strong")


class TestRoutingCost(unittest.TestCase):
    """Cost preference routing."""

    def setUp(self) -> None:
        self.registry = _make_registry("ollama", "openai", "free_remote")
        self.router = ModelRouter(self.registry)

    def test_low_cost_prefers_free_provider(self) -> None:
        ctx = RoutingContext(cost_preference="low")
        decision = self.router.route(ctx)
        meta = self.registry[decision.provider_name]
        self.assertEqual(meta.cost_class, CostClass.FREE)

    def test_no_paid_constraint_excludes_paid(self) -> None:
        ctx = RoutingContext(constraints=("no_paid",))
        decision = self.router.route(ctx)
        self.assertNotEqual(decision.provider_name, "openai")
        self.assertNotIn("openai", decision.fallback_chain)


class TestRoutingAvailability(unittest.TestCase):
    """Provider availability handling."""

    def test_unavailable_provider_is_excluded(self) -> None:
        registry = _make_registry("ollama", "unavailable")
        router = ModelRouter(registry)
        ctx = RoutingContext()
        decision = router.route(ctx)
        self.assertEqual(decision.provider_name, "ollama")
        self.assertNotIn("unavailable", decision.fallback_chain)

    def test_all_unavailable_raises(self) -> None:
        registry = _make_registry("unavailable")
        router = ModelRouter(registry)
        ctx = RoutingContext()
        with self.assertRaises(RoutingError):
            router.route(ctx)


class TestRoutingComplexity(unittest.TestCase):
    """Complexity-based routing."""

    def test_simple_request_prefers_local(self) -> None:
        registry = _make_registry("ollama", "openai")
        router = ModelRouter(registry)
        ctx = RoutingContext(complexity="simple")
        decision = router.route(ctx)
        self.assertEqual(decision.provider_name, "ollama")


# ------------------------------------------------------------------
# Gateway integration tests (using fake providers)
# ------------------------------------------------------------------


class FakeProvider:
    """Minimal provider for gateway integration tests."""

    def __init__(self, name: str, should_fail: bool = False) -> None:
        self._name = name
        self._should_fail = should_fail
        self.call_count = 0

    def complete(self, request: AIRequest) -> AIResponse:
        self.call_count += 1
        if self._should_fail:
            from ai.errors import ProviderError

            raise ProviderError(f"{self._name} simulated failure")
        return AIResponse(
            content=f"Response from {self._name}",
            model_used=f"{self._name}-model",
        )


class TestGatewayRoutingIntegration(unittest.TestCase):
    """Test the full gateway -> router -> provider path with fakes."""

    def _make_gateway(self, providers: dict[str, FakeProvider]) -> DefaultAIGateway:
        """Build a DefaultAIGateway with injected fake providers."""
        from ai.gateway.default_gateway import DefaultAIGateway

        # Bypass __init__ to inject fakes
        gw = object.__new__(DefaultAIGateway)
        gw._providers = providers  # type: ignore[assignment,attr-defined]
        gw._metadata = {
            name: ProviderMetadata(
                name=name,
                locality=Locality.LOCAL if "local" in name else Locality.REMOTE,
                cost_class=CostClass.FREE if "free" in name or "local" in name else CostClass.PAID,
                quality_class=QualityClass.HIGH if "strong" in name else QualityClass.STANDARD,
            )
            for name in providers
        }
        gw._router = ModelRouter(gw._metadata)  # type: ignore[attr-defined]
        return gw

    def test_generate_routes_to_provider(self) -> None:
        local = FakeProvider("local")
        gw = self._make_gateway({"local": local})
        req = AIRequest(messages=[AIMessage(role="user", content="hi")])
        resp = gw.generate(req)
        self.assertEqual(resp.content, "Response from local")
        self.assertEqual(local.call_count, 1)

    def test_generate_fallback_on_failure(self) -> None:
        failing = FakeProvider("local_failing", should_fail=True)
        backup = FakeProvider("local_backup")
        gw = self._make_gateway({"local_failing": failing, "local_backup": backup})
        req = AIRequest(messages=[AIMessage(role="user", content="hi")])
        resp = gw.generate(req)
        self.assertEqual(resp.content, "Response from local_backup")

    def test_generate_respects_privacy_on_fallback(self) -> None:
        """Remote fallback must be skipped when privacy=local_only."""
        failing_local = FakeProvider("local", should_fail=True)
        remote = FakeProvider("remote_strong")
        gw = self._make_gateway({"local": failing_local, "remote_strong": remote})
        req = AIRequest(
            messages=[AIMessage(role="user", content="private data")],
            options={"routing": {"privacy": "local_only"}},
        )
        from ai.errors import ProviderError

        with self.assertRaises(ProviderError):
            gw.generate(req)
        # Remote provider must NOT have been called
        self.assertEqual(remote.call_count, 0)

    def test_routing_hints_via_options(self) -> None:
        local = FakeProvider("local")
        remote = FakeProvider("remote_strong")
        gw = self._make_gateway({"local": local, "remote_strong": remote})
        req = AIRequest(
            messages=[AIMessage(role="user", content="hard question")],
            options={"routing": {"quality": "high"}},
        )
        resp = gw.generate(req)
        self.assertEqual(resp.content, "Response from remote_strong")


# ------------------------------------------------------------------
# Backward compatibility
# ------------------------------------------------------------------


class TestBackwardCompatibility(unittest.TestCase):
    """Ensure S3/S4 behaviour is preserved."""

    def test_cognition_stub_still_works(self) -> None:
        from capabilities.cognition.cognition import CognitionCapability
        from core.contracts.capability import Request

        cog = CognitionCapability()  # no gateway
        req = Request(request_id="compat_01", payload={"prompt": "test"})
        res = cog.invoke(req)
        self.assertTrue(res.success)
        self.assertIn("Cognition S1 Stub", res.data["reply"])

    def test_cognition_with_fake_gateway_still_works(self) -> None:
        from capabilities.cognition.cognition import CognitionCapability
        from core.contracts.ai import AIGateway
        from core.contracts.capability import Request

        class FakeGW(AIGateway):
            def generate(self, request: AIRequest) -> AIResponse:
                return AIResponse(content="ok", model_used="fake")

        cog = CognitionCapability(gateway=FakeGW())
        req = Request(request_id="compat_02", payload={"prompt": "test"})
        res = cog.invoke(req)
        self.assertTrue(res.success)
        self.assertEqual(res.data["reply"], "ok")


if __name__ == "__main__":
    unittest.main()
