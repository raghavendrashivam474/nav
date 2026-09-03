from unittest import TestCase

from core.contracts.capability import Capability, Request, Response


class ConcreteCapability(Capability):
    @property
    def name(self) -> str:
        return "test_cap"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "A test capability"

    def invoke(self, request: Request) -> Response:
        return Response(request_id=request.request_id, data={"echo": request.payload.get("msg")})


class TestCapabilityContracts(TestCase):
    def test_request_instantiation(self):
        req = Request(request_id="req-123", payload={"msg": "hello"})
        self.assertEqual(req.request_id, "req-123")
        self.assertEqual(req.payload, {"msg": "hello"})

    def test_response_defaults(self):
        res = Response(request_id="req-123")
        self.assertEqual(res.request_id, "req-123")
        self.assertTrue(res.success)
        self.assertIsNone(res.error)
        self.assertEqual(res.data, {})

    def test_capability_subclass(self):
        cap = ConcreteCapability()
        self.assertEqual(cap.name, "test_cap")
        self.assertIn("1.0.0", cap.version)
        self.assertIn("test capability", cap.description)

        req = Request(request_id="req-1", payload={"msg": "ping"})
        res = cap.invoke(req)
        self.assertTrue(res.success)
        self.assertEqual(res.data["echo"], "ping")
