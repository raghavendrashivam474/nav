from core.contracts.capability import Capability, Request, Response

class CognitionCapability(Capability):
    @property
    def name(self) -> str:
        return 'cognition'

    @property
    def version(self) -> str:
        return '0.1.0'

    @property
    def description(self) -> str:
        return 'Primary reasoning and response generation capability for NAV.'

    def invoke(self, request: Request) -> Response:
        prompt = request.payload.get('prompt', '')
        return Response(request_id=request.request_id, data={'reply': f'Cognition S1 Stub: Received prompt -> {prompt}'}, success=True)
