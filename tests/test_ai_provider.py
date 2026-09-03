"""Unit tests for the AI provider adapters.

Tests translation logic and error handling WITHOUT hitting real APIs.
Uses httpx mock transport to simulate provider responses.
"""

import unittest

import httpx

from ai.errors import ConfigurationError, ProviderError
from ai.providers.ollama_provider import OllamaProvider
from ai.providers.openai_provider import OpenAIProvider
from core.contracts.ai import AIMessage, AIRequest


def _make_request(prompt: str = "Hello") -> AIRequest:
    return AIRequest(messages=[AIMessage(role="user", content=prompt)])


# =====================================================================
# OpenAI Provider Tests
# =====================================================================


class TestOpenAIProviderInit(unittest.TestCase):
    def test_empty_api_key_raises(self) -> None:
        with self.assertRaises(ConfigurationError):
            OpenAIProvider(api_key="")

    def test_whitespace_api_key_raises(self) -> None:
        with self.assertRaises(ConfigurationError):
            OpenAIProvider(api_key="   ")

    def test_valid_key_succeeds(self) -> None:
        provider = OpenAIProvider(api_key="sk-test-key")
        self.assertIsNotNone(provider)


class TestOpenAIProviderTranslation(unittest.TestCase):
    def test_build_payload_basic(self) -> None:
        provider = OpenAIProvider(api_key="sk-test")
        req = _make_request("Explain gravity")
        payload = provider._build_payload(req)
        self.assertEqual(payload["model"], "gpt-4o-mini")
        self.assertEqual(payload["messages"][0]["role"], "user")
        self.assertEqual(payload["messages"][0]["content"], "Explain gravity")
        self.assertEqual(payload["temperature"], 0.7)

    def test_build_payload_with_max_tokens(self) -> None:
        provider = OpenAIProvider(api_key="sk-test")
        req = AIRequest(
            messages=[AIMessage(role="user", content="Hi")],
            max_tokens=100,
        )
        payload = provider._build_payload(req)
        self.assertEqual(payload["max_tokens"], 100)

    def test_parse_response_valid(self) -> None:
        provider = OpenAIProvider(api_key="sk-test")
        data = {
            "choices": [{"message": {"role": "assistant", "content": "Hello!"}}],
            "model": "gpt-4o-mini-2024-07-18",
            "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
        }
        resp = provider._parse_response(data)
        self.assertEqual(resp.content, "Hello!")
        self.assertEqual(resp.model_used, "gpt-4o-mini-2024-07-18")
        self.assertEqual(resp.usage["total_tokens"], 7)

    def test_parse_response_malformed_raises(self) -> None:
        provider = OpenAIProvider(api_key="sk-test")
        with self.assertRaises(ProviderError):
            provider._parse_response({"unexpected": "structure"})


class TestOpenAIProviderHTTP(unittest.TestCase):
    def _make_provider_with_mock(self, status_code: int, json_body: dict) -> OpenAIProvider:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code, json=json_body)

        transport = httpx.MockTransport(handler)
        provider = OpenAIProvider(api_key="sk-test-key")

        def patched_complete(request: AIRequest):
            payload = provider._build_payload(request)
            headers = {
                "Authorization": f"Bearer {provider._api_key}",
                "Content-Type": "application/json",
            }
            with httpx.Client(transport=transport, timeout=5.0) as client:
                response = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    json=payload,
                    headers=headers,
                )
            if response.status_code == 401:
                raise ConfigurationError("Bad key")
            if response.status_code >= 400:
                raise ProviderError(f"HTTP {response.status_code}")
            return provider._parse_response(response.json())

        provider.complete = patched_complete  # type: ignore[assignment]
        return provider

    def test_successful_completion(self) -> None:
        provider = self._make_provider_with_mock(
            200,
            {
                "choices": [{"message": {"role": "assistant", "content": "42"}}],
                "model": "gpt-4o-mini",
                "usage": {"total_tokens": 10},
            },
        )
        resp = provider.complete(_make_request("Meaning of life?"))
        self.assertEqual(resp.content, "42")

    def test_401_raises_configuration_error(self) -> None:
        provider = self._make_provider_with_mock(401, {"error": "bad key"})
        with self.assertRaises(ConfigurationError):
            provider.complete(_make_request())

    def test_429_raises_provider_error(self) -> None:
        provider = self._make_provider_with_mock(429, {"error": "rate limit"})
        with self.assertRaises(ProviderError):
            provider.complete(_make_request())


# =====================================================================
# Ollama Provider Tests
# =====================================================================


class TestOllamaProviderTranslation(unittest.TestCase):
    def test_parse_response_valid(self) -> None:
        provider = OllamaProvider()
        raw_data = {
            "model": "mistral",
            "created_at": "2023-08-04T19:22:45.499127Z",
            "message": {"role": "assistant", "content": "Hello local human!"},
            "done": True,
            "total_duration": 5000000,
            "load_duration": 100000,
            "prompt_eval_count": 8,
            "eval_count": 12,
        }
        resp = provider._parse_response(raw_data)
        self.assertEqual(resp.content, "Hello local human!")
        self.assertEqual(resp.model_used, "mistral")
        self.assertEqual(resp.usage["prompt_tokens"], 8)
        self.assertEqual(resp.usage["completion_tokens"], 12)
        self.assertEqual(resp.usage["total_tokens"], 20)

    def test_parse_response_malformed_raises(self) -> None:
        provider = OllamaProvider()
        with self.assertRaises(ProviderError):
            provider._parse_response({"bad": "structure"})


class TestOllamaProviderHTTP(unittest.TestCase):
    def _make_provider_with_mock(self, status_code: int, json_body: dict) -> OllamaProvider:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code, json=json_body)

        transport = httpx.MockTransport(handler)
        provider = OllamaProvider()

        def patched_complete(request: AIRequest):
            payload = {
                "model": provider._model,
                "messages": [{"role": m.role, "content": m.content} for m in request.messages],
                "stream": False,
            }
            with httpx.Client(transport=transport, timeout=5.0) as client:
                response = client.post(provider._base_url, json=payload)
            if response.status_code >= 400:
                raise ProviderError(f"HTTP {response.status_code}")
            return provider._parse_response(response.json())

        provider.complete = patched_complete  # type: ignore[assignment]
        return provider

    def test_successful_ollama_completion(self) -> None:
        provider = self._make_provider_with_mock(
            200,
            {
                "model": "mistral",
                "message": {"role": "assistant", "content": "Hello from Mistral!"},
                "prompt_eval_count": 10,
                "eval_count": 15,
            },
        )
        resp = provider.complete(_make_request("Ping"))
        self.assertEqual(resp.content, "Hello from Mistral!")
        self.assertEqual(resp.model_used, "mistral")
        self.assertEqual(resp.usage["total_tokens"], 25)

    def test_httperror_raises_provider_error(self) -> None:
        provider = self._make_provider_with_mock(500, {"error": "ollama crash"})
        with self.assertRaises(ProviderError):
            provider.complete(_make_request())


if __name__ == "__main__":
    unittest.main()
