"""Unit tests for the upgraded Cognition capability.

Uses a FakeAIGateway so the full test suite never touches a live API.
"""

import unittest

from capabilities.cognition.cognition import CognitionCapability
from core.contracts.ai import AIGateway, AIRequest, AIResponse
from core.contracts.capability import Request


class FakeAIGateway(AIGateway):
    """Deterministic fake that returns a canned response."""

    def __init__(self, reply: str = "Fake AI reply") -> None:
        self._reply = reply
        self.last_request: AIRequest | None = None

    def generate(self, request: AIRequest) -> AIResponse:
        self.last_request = request
        return AIResponse(
            content=self._reply,
            model_used="fake-model-v1",
            usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        )


class FailingAIGateway(AIGateway):
    """Gateway that always raises."""

    def generate(self, request: AIRequest) -> AIResponse:
        raise RuntimeError("Simulated provider failure")


class TestCognitionWithGateway(unittest.TestCase):
    """Cognition wired to a real (fake) gateway."""

    def setUp(self) -> None:
        self.fake_gw = FakeAIGateway(reply="The sky is blue because Rayleigh scattering.")
        self.cognition = CognitionCapability(gateway=self.fake_gw)

    def test_invoke_returns_ai_reply(self) -> None:
        req = Request(request_id="s3_01", payload={"prompt": "Why is the sky blue?"})
        res = self.cognition.invoke(req)
        self.assertTrue(res.success)
        self.assertIn("Rayleigh", res.data["reply"])
        self.assertEqual(res.data["model"], "fake-model-v1")

    def test_invoke_passes_prompt_to_gateway(self) -> None:
        req = Request(request_id="s3_02", payload={"prompt": "Hello NAV"})
        self.cognition.invoke(req)
        self.assertIsNotNone(self.fake_gw.last_request)
        self.assertEqual(self.fake_gw.last_request.messages[0].content, "Hello NAV")
        self.assertEqual(self.fake_gw.last_request.messages[0].role, "user")

    def test_invoke_empty_prompt_fails(self) -> None:
        req = Request(request_id="s3_03", payload={"prompt": "   "})
        res = self.cognition.invoke(req)
        self.assertFalse(res.success)
        self.assertIn("Empty prompt", res.error)

    def test_invoke_preserves_request_id(self) -> None:
        req = Request(request_id="s3_04", payload={"prompt": "test"})
        res = self.cognition.invoke(req)
        self.assertEqual(res.request_id, "s3_04")

    def test_gateway_failure_returns_error_response(self) -> None:
        cognition = CognitionCapability(gateway=FailingAIGateway())
        req = Request(request_id="s3_05", payload={"prompt": "test"})
        res = cognition.invoke(req)
        self.assertFalse(res.success)
        self.assertIn("AI generation failed", res.error)


class TestCognitionStubFallback(unittest.TestCase):
    """Cognition without a gateway falls back to S1 stub."""

    def setUp(self) -> None:
        self.cognition = CognitionCapability()  # no gateway

    def test_stub_returns_echo(self) -> None:
        req = Request(request_id="s3_06", payload={"prompt": "Ping"})
        res = self.cognition.invoke(req)
        self.assertTrue(res.success)
        self.assertIn("Cognition S1 Stub", res.data["reply"])

    def test_version_bumped(self) -> None:
        self.assertEqual(self.cognition.version, "0.2.0")


if __name__ == "__main__":
    unittest.main()
