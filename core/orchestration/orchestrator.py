import logging
from core.contracts.capability import Request, Response
from core.capabilities.registry import CapabilityRegistry

logger = logging.getLogger('NAV.Orchestrator')

class Orchestrator:
    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    def route_request(self, target_capability: str, request: Request) -> Response:
        try:
            capability = self.registry.get(target_capability)
            logger.info(f"Routing request '{request.request_id}' to '{target_capability}'")
            return capability.invoke(request)
        except Exception as e:
            logger.error(f"Routing failed for '{target_capability}': {str(e)}")
            return Response(request_id=request.request_id, data={}, success=False, error=f"Orchestration failure: {str(e)}")
