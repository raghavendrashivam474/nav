import logging

from core.capabilities.registry import CapabilityRegistry
from core.contracts.capability import Request, Response

logger = logging.getLogger("NAV.Orchestrator")


class Orchestrator:
    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    def route_request(self, target_capability: str, request: Request) -> Response:
        try:
            capability = self.registry.get(target_capability)
            return capability.invoke(request)
        except Exception as e:
            logger.error(f"Routing failed for '{target_capability}': {e!s}")
            return Response(
                request_id=request.request_id,
                data={},
                success=False,
                error=f"Orchestration failure: {e!s}",
            )
