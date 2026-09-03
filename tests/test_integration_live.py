"""Live integration test — tests the active configured provider.

By default, tests Ollama on localhost:11434. If NAV_AI_PROVIDER=openai
is configured and keys are present, tests OpenAI.

Skipped if the local Ollama instance is not running or if keys are missing.
"""

import os
import unittest

import httpx

from ai.gateway.default_gateway import DefaultAIGateway
from capabilities.cognition.cognition import CognitionCapability
from core.capabilities.registry import CapabilityRegistry
from core.contracts.capability import Request
from core.orchestration.orchestrator import Orchestrator

PROVIDER = os.environ.get("NAV_AI_PROVIDER", "ollama").lower()


def is_ollama_running() -> bool:
    """Helper to detect if local Ollama service is up."""
    try:
        resp = httpx.get("http://localhost:11434")
        return resp.status_code == 200
    except Exception:
        return False


def can_run_test() -> bool:
    if PROVIDER == "ollama":
        return is_ollama_running()
    if PROVIDER == "openai":
        return bool(os.environ.get("NAV_OPENAI_API_KEY"))
    return False


@unittest.skipUnless(can_run_test(), "Active AI provider is not running or credentials missing")
class TestLiveAIIntegration(unittest.TestCase):
    """Full NAV -> Cognition -> Gateway -> Active Provider -> Model round-trip."""

    def setUp(self) -> None:
        self.gateway = DefaultAIGateway()
        self.cognition = CognitionCapability(gateway=self.gateway)
        self.registry = CapabilityRegistry()
        self.registry.register(self.cognition)
        self.orchestrator = Orchestrator(self.registry)

    def test_end_to_end_cognition(self) -> None:
        prompt = "Say exactly: NAV is alive."
        if PROVIDER == "ollama":
            # Loosen instruction following for smaller local models
            prompt = "Say 'NAV is alive'"

        req = Request(
            request_id="live_01",
            payload={"prompt": prompt, "temperature": 0.0},
        )
        res = self.orchestrator.route_request("cognition", req)
        self.assertTrue(res.success, f"Failed: {res.error}")

        reply = res.data.get("reply", "").strip()
        self.assertGreater(len(reply), 0, "Model returned an empty response.")
        self.assertIn("model", res.data)

        # Log the real output for developer visual inspection
        print(f"\n[Live Response from {res.data['model']}]: {reply}")
