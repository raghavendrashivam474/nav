"""Cognition capability â€” NAV's primary reasoning engine.

S1: Stub that echoed the prompt.
S3: Real AI-powered cognition via the AIGateway contract.
S6: Optional memory integration â€” retrieves context and handles
    explicit remember/forget requests.

When no gateway is injected the capability falls back to the S1 stub
behaviour so that existing tests continue to pass without a live API.
"""

from __future__ import annotations

import uuid

from core.contracts.ai import AIGateway, AIMessage, AIRequest
from core.contracts.capability import Capability, Request, Response
from core.contracts.memory import MemoryCapabilityInterface, MemoryQuery, MemoryRecord
from core.log import get_logger

logger = get_logger(__name__)


class CognitionCapability(Capability):
    """Understand requests, reason via an AI model, and produce responses."""

    def __init__(
        self,
        gateway: AIGateway | None = None,
        memory: MemoryCapabilityInterface | None = None,
    ) -> None:
        self._gateway = gateway
        self._memory = memory

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

        # --- S6: Handle explicit memory commands before AI call ---
        if self._memory is not None:
            memory_response = self._handle_memory(request, prompt)
            if memory_response is not None:
                return memory_response

        if self._gateway is None:
            return self._stub_response(request, prompt)

        return self._ai_response(request, prompt)

    # ------------------------------------------------------------------
    # S6: Memory integration
    # ------------------------------------------------------------------

    def _handle_memory(self, request: Request, prompt: str) -> Response | None:
        """Intercept remember/forget requests.  Returns None to continue
        normal AI processing when the prompt is not a memory command."""
        assert self._memory is not None

        # --- FORGET ---
        if self._memory and self._is_forget(prompt):
            return self._do_forget(request, prompt)

        # --- REMEMBER ---
        if self._memory and self._is_remember(prompt):
            return self._do_remember(request, prompt)

        return None  # not a memory command â†’ continue to AI

    @staticmethod
    def _is_remember(text: str) -> bool:
        import re

        return bool(re.search(r"\bremember\s+(?:that\s+)?", text, re.IGNORECASE))

    @staticmethod
    def _is_forget(text: str) -> bool:
        import re

        return bool(re.search(r"\bforget\b", text, re.IGNORECASE))

    def _do_remember(self, request: Request, prompt: str) -> Response:
        assert self._memory is not None
        import re

        # Extract content after "remember [that]"
        m = re.search(r"\bremember\s+(?:that\s+)?(.+)", prompt, re.IGNORECASE)
        content = m.group(1).strip().rstrip(".") if m else prompt.strip()

        key = f"mem_{uuid.uuid4().hex[:12]}"
        record = MemoryRecord(
            key=key,
            value=content,
            tags=["user", "conversation"],
            metadata={"source": "explicit_remember", "importance": 0.8, "confidence": 0.9},
        )
        ok = self._memory.store(record)
        reply = "Remembered." if ok else "I couldn't store that memory."
        logger.info("Memory stored via cognition: %s (ok=%s)", key, ok)
        return Response(
            request_id=request.request_id,
            data={"reply": reply, "memory_key": key},
            success=ok,
        )

    def _do_forget(self, request: Request, prompt: str) -> Response:
        assert self._memory is not None
        import re

        # Try to extract search terms after "forget [that/this]"
        cleaned = (
            re.sub(
                r"\bforget\s+(?:that|this|everything\s+about)?\s*",
                "",
                prompt,
                flags=re.IGNORECASE,
            )
            .strip()
            .rstrip("?!.")
        )

        if cleaned:
            # Search for matching memories and delete the best match
            results = self._memory.retrieve(MemoryQuery(query_text=cleaned, limit=1))
        else:
            # "Forget that" with no specifics â†’ delete most recent
            results = self._memory.retrieve(MemoryQuery(limit=1))

        if not results:
            return Response(
                request_id=request.request_id,
                data={"reply": "I don't have a matching memory to forget."},
                success=True,
            )

        target = results[0]
        ok = self._memory.forget(target.key)
        reply = "Forgotten." if ok else "I couldn't remove that memory."
        logger.info("Memory forgotten via cognition: %s (ok=%s)", target.key, ok)
        return Response(
            request_id=request.request_id,
            data={"reply": reply, "memory_key": target.key},
            success=ok,
        )

    # ------------------------------------------------------------------
    # Real AI path (S3 + S6 context injection)
    # ------------------------------------------------------------------

    def _ai_response(self, request: Request, prompt: str) -> Response:
        assert self._gateway is not None
        if not prompt.strip():
            return Response(
                request_id=request.request_id,
                data={"reply": ""},
                success=False,
                error="Empty prompt",
            )

        # --- S6: Inject relevant memories into context ---
        enriched_prompt = self._enrich_with_memories(prompt)

        ai_request = AIRequest(
            messages=[AIMessage(role="user", content=enriched_prompt)],
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

    def _enrich_with_memories(self, prompt: str) -> str:
        """Prepend relevant memories to the prompt if available."""
        if self._memory is None:
            return prompt

        try:
            # Extract a few keywords for search (simple: use the whole prompt)
            results = self._memory.retrieve(MemoryQuery(query_text=prompt[:100], limit=5))
            if not results:
                return prompt

            memory_lines = [f"- {r.value}" for r in results]
            context_block = (
                "[Relevant memories from previous conversations]\n"
                + "\n".join(memory_lines)
                + "\n[End of memories]\n\n"
            )
            return context_block + prompt
        except Exception as exc:
            logger.warning("Memory retrieval failed (non-fatal): %s", exc)
            return prompt

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
