"""Memory capability — registered in the CapabilityRegistry.

Implements both the generic `Capability` contract (for Orchestrator
routing) and `MemoryCapabilityInterface` (for direct use by Cognition).
"""

from __future__ import annotations

from capabilities.memory.service import MemoryService
from core.contracts.capability import Capability, Request, Response
from core.contracts.memory import MemoryCapabilityInterface, MemoryQuery, MemoryRecord
from core.log import get_logger

logger = get_logger(__name__)


class MemoryCapability(Capability, MemoryCapabilityInterface):
    """Persistent memory for NAV, backed by a replaceable MemoryService."""

    def __init__(self, service: MemoryService) -> None:
        self._service = service

    # ------------------------------------------------------------------
    # Capability metadata
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "memory"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def description(self) -> str:
        return "Persistent memory storage and retrieval for NAV."

    # ------------------------------------------------------------------
    # MemoryCapabilityInterface delegation
    # ------------------------------------------------------------------

    def store(self, record: MemoryRecord) -> bool:
        return self._service.store(record)

    def retrieve(self, query: MemoryQuery) -> list[MemoryRecord]:
        return self._service.retrieve(query)

    def update(self, record: MemoryRecord) -> bool:
        return self._service.update(record)

    def forget(self, key: str) -> bool:
        return self._service.forget(key)

    # ------------------------------------------------------------------
    # Capability contract (Orchestrator-facing)
    # ------------------------------------------------------------------

    def invoke(self, request: Request) -> Response:
        action = request.payload.get("action", "")
        try:
            if action == "store":
                record = MemoryRecord(
                    key=request.payload["key"],
                    value=request.payload["value"],
                    tags=request.payload.get("tags", []),
                    metadata=request.payload.get("metadata", {}),
                )
                ok = self.store(record)
                return Response(
                    request_id=request.request_id,
                    data={"stored": ok},
                    success=ok,
                )

            if action == "retrieve":
                query = MemoryQuery(
                    query_text=request.payload.get("query_text"),
                    tags=request.payload.get("tags", []),
                    limit=request.payload.get("limit", 10),
                )
                records = self.retrieve(query)
                return Response(
                    request_id=request.request_id,
                    data={
                        "memories": [
                            {
                                "key": r.key,
                                "value": r.value,
                                "tags": r.tags,
                                "metadata": r.metadata,
                            }
                            for r in records
                        ]
                    },
                    success=True,
                )

            if action == "update":
                record = MemoryRecord(
                    key=request.payload["key"],
                    value=request.payload["value"],
                    tags=request.payload.get("tags", []),
                    metadata=request.payload.get("metadata", {}),
                )
                ok = self.update(record)
                return Response(
                    request_id=request.request_id,
                    data={"updated": ok},
                    success=ok,
                )

            if action == "forget":
                key = request.payload["key"]
                ok = self.forget(key)
                return Response(
                    request_id=request.request_id,
                    data={"forgotten": ok},
                    success=ok,
                )

            return Response(
                request_id=request.request_id,
                data={},
                success=False,
                error=f"Unknown memory action: {action}",
            )

        except KeyError as exc:
            return Response(
                request_id=request.request_id,
                data={},
                success=False,
                error=f"Missing required field: {exc}",
            )
        except Exception as exc:
            logger.error("Memory invoke failed: %s", exc)
            return Response(
                request_id=request.request_id,
                data={},
                success=False,
                error=f"Memory operation failed: {exc}",
            )
