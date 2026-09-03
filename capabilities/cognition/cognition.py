"""Cognition capability — NAV's primary reasoning engine.

S1: Stub that echoed the prompt.
S3: Real AI-powered cognition via the AIGateway contract.

When no gateway is injected the capability falls back to the S1 stub
behaviour so that existing tests continue to pass without a live API.
"""

from __future__ import annotations

from core.contracts.ai import AIGateway, AIMessage, AIRequest
from core.contracts.capability import Capability, Request, Response
from core.log import get_logger

logger = get_logger(__name__)


class CognitionCapability(Capability):
    """Understand requests, reason via an AI model, and produce responses."""

    def __init__(self, gateway: AIGateway | None = None) -> None:
        self._gateway = gateway

    # ------------------------------------------------------------------
    # Capability contract
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "cognition"

    @property
    def version(self) -> str:
        return "0.2.0"

    @property
    def description(self) -> str:
        return "Primary reasoning and response generation capability for NAV."

    def invoke(self, request: Request) -> Response:
        prompt = request.payload.get("prompt", "")
        logger.info("Cognition request received (id=%s)", request.request_id)

        if self._gateway is None:
            return self._stub_response(request, prompt)

        return self._ai_response(request, prompt)

    # ------------------------------------------------------------------
    # Real AI path (S3)
    # ------------------------------------------------------------------

    def _ai_response(self, request: Request, prompt: str) -> Response:
        assert self._gateway is not None  # guarded by invoke()
        if not prompt.strip():
            return Response(
                request_id=request.request_id,
                data={"reply": ""},
                success=False,
                error="Empty prompt",
            )

        ai_request = AIRequest(
            messages=[AIMessage(role="user", content=prompt)],
            temperature=request.payload.get("temperature", 0.7),
        )

        try:
            ai_response = self._gateway.generate(ai_request)
        except Exception as exc:
            logger.error("Cognition AI call failed: %s", exc)
            return Response(
                request_id=request.request_id,
                data={},
                success=False,
                error=f"AI generation failed: {exc}",
            )

        logger.info("Cognition AI response received (model=%s)", ai_response.model_used)
        return Response(
            request_id=request.request_id,
            data={
                "reply": ai_response.content,
                "model": ai_response.model_used,
                "usage": ai_response.usage,
            },
            success=True,
        )

    # ------------------------------------------------------------------
    # Stub fallback (S1 backward compatibility)
    # ------------------------------------------------------------------

    @staticmethod
    def _stub_response(request: Request, prompt: str) -> Response:
        logger.debug("Cognition running in stub mode (no gateway)")
        return Response(
            request_id=request.request_id,
            data={"reply": f"Cognition S1 Stub: Received prompt -> {prompt}"},
            success=True,
        )
