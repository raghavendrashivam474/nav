"""Tests for the Cognition capability (S3 real AI generation + S1 fallback)."""

from unittest import TestCase

from capabilities.cognition.cognition import CognitionCapability
from core.contracts.ai import AIGateway, AIRequest, AIResponse
from core.contracts.capability import Request


class FakeAIGateway(AIGateway):
    """Test fake for AIGateway."""

    def __init__(self, response_text: str = "Fake answer", model: str = "fake-model") -> None:
        self.response_text = response_text
        self.model = model
        self.last_request: AIRequest | None = None

    def generate(self, request: AIRequest) -> AIResponse:
        self.last_request = request
        return AIResponse(
            content=self.response_text,
            model_used=self.model,
            usage={"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
        )


class FailingAIGateway(AIGateway):
    """Test fake that always raises an error."""

    def generate(self, request: AIRequest) -> AIResponse:
        raise RuntimeError("Gateway connection failed")


class TestCognitionCapability(TestCase):
    def test_metadata(self) -> None:
        cap = CognitionCapability()
        self.assertEqual(cap.name, "cognition")
        self.assertEqual(cap.version, "0.2.0")
        self.assertTrue(len(cap.description) > 0)

    def test_ai_response_with_gateway(self) -> None:
        fake_gw = FakeAIGateway(response_text="Paris", model="mistral")
        cap = CognitionCapability(gateway=fake_gw)

        req = Request(
            request_id="req-1",
            payload={"prompt": "What is the capital of France?", "temperature": 0.5},
        )
        res = cap.invoke(req)

        self.assertTrue(res.success)
        self.assertEqual(res.data["reply"], "Paris")
        self.assertEqual(res.data["model"], "mistral")

        last_req = fake_gw.last_request
        self.assertIsNotNone(last_req)
        assert last_req is not None
        self.assertEqual(len(last_req.messages), 1)
        self.assertEqual(last_req.messages[0].content, "What is the capital of France?")
        self.assertEqual(last_req.temperature, 0.5)

    def test_empty_prompt_returns_error(self) -> None:
        fake_gw = FakeAIGateway()
        cap = CognitionCapability(gateway=fake_gw)

        req = Request(request_id="req-2", payload={"prompt": ""})
        res = cap.invoke(req)

        self.assertFalse(res.success)
        err = res.error
        self.assertIsNotNone(err)
        assert err is not None
        self.assertIn("Empty prompt", err)

    def test_gateway_failure_returns_error_response(self) -> None:
        failing_gw = FailingAIGateway()
        cap = CognitionCapability(gateway=failing_gw)

        req = Request(request_id="req-3", payload={"prompt": "Hello"})
        res = cap.invoke(req)

        self.assertFalse(res.success)
        err = res.error
        self.assertIsNotNone(err)
        assert err is not None
        self.assertIn("Gateway connection failed", err)

    def test_stub_fallback_without_gateway(self) -> None:
        """Preserve S1 backward compatibility when no gateway is injected."""
        cap = CognitionCapability()

        req = Request(request_id="req-4", payload={"prompt": "Hello stub"})
        res = cap.invoke(req)

        self.assertTrue(res.success)
        self.assertIn("Cognition S1 Stub", res.data["reply"])
        self.assertIn("Hello stub", res.data["reply"])
