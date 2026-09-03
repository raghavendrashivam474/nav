import unittest
from core.contracts.capability import Request
from core.capabilities.registry import CapabilityRegistry
from core.orchestration.orchestrator import Orchestrator
from capabilities.cognition.cognition import CognitionCapability

class TestNAVArchitectureSkeleton(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = CapabilityRegistry()
        self.orchestrator = Orchestrator(self.registry)
        self.cognition = CognitionCapability()

    def test_capability_registration(self) -> None:
        self.registry.register(self.cognition)
        self.assertIn('cognition', self.registry.list_capabilities())
        self.assertEqual(self.registry.get('cognition'), self.cognition)

    def test_duplicate_registration_raises_error(self) -> None:
        self.registry.register(self.cognition)
        with self.assertRaises(ValueError):
            self.registry.register(self.cognition)

    def test_orchestrator_routes_correctly(self) -> None:
        self.registry.register(self.cognition)
        req = Request(request_id='tx_101', payload={'prompt': 'Ping'})
        res = self.orchestrator.route_request('cognition', req)
        self.assertTrue(res.success)
        self.assertEqual(res.request_id, 'tx_101')
        self.assertIn('Cognition S1 Stub', res.data.get('reply', ''))

    def test_orchestrator_handles_missing_capability(self) -> None:
        req = Request(request_id='tx_102')
        res = self.orchestrator.route_request('unregistered_service', req)
        self.assertFalse(res.success)
        self.assertIn('not registered', res.error)

if __name__ == '__main__':
    unittest.main()
