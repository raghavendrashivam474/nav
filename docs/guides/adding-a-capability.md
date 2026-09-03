# Guide: Adding a New Capability to NAV

This guide walks you through adding a new capability to NAV from scratch, using the established patterns from S1 and S2.

---

## Overview

Every capability in NAV follows the same lifecycle:
Define → Implement → Register → Route → Test

text


---

## Step 1: Create the Capability Directory

Create a new directory under `capabilities/`:

```powershell
New-Item -ItemType Directory -Path "capabilities\my_capability" -Force
Create the required __init__.py:

PowerShell

New-Item -ItemType File -Path "capabilities\my_capability\__init__.py" -Force
Step 2: Implement the Capability
Create capabilities/my_capability/my_capability.py:

Python

from core.contracts.capability import Capability, Request, Response
from core.log import get_logger

logger = get_logger(__name__)


class MyCapability(Capability):
    """Example capability demonstrating the NAV pattern."""

    @property
    def name(self) -> str:
        return "my_capability"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def description(self) -> str:
        return "An example capability for demonstration purposes."

    def invoke(self, request: Request) -> Response:
        logger.info(f"Invoking {self.name} for request {request.request_id}")

        # Extract input from the request payload
        input_data = request.payload.get("input", "")

        # Process the input (replace with real logic)
        result = f"Processed: {input_data}"

        return Response(
            request_id=request.request_id,
            data={"result": result},
            success=True,
        )
Key Rules
Subclass Capability from core.contracts.capability.
Implement all four abstract members: name, version, description, invoke.
Use get_logger(__name__) for all logging.
Return a Response with the matching request_id.
Never import vendor packages directly in the capability. Use the AI Gateway if you need AI.
Step 3: Register the Capability
In your application entry point or initialization code:

Python

from core.capabilities.registry import CapabilityRegistry
from capabilities.my_capability.my_capability import MyCapability

registry = CapabilityRegistry()
registry.register(MyCapability())

print(registry.list_capabilities())
# Output: ["my_capability"]
Step 4: Route Requests Through the Orchestrator
Python

from core.orchestration.orchestrator import Orchestrator
from core.contracts.capability import Request

orchestrator = Orchestrator(registry)

request = Request(
    request_id="req_001",
    payload={"input": "Hello, NAV!"},
)

response = orchestrator.route_request("my_capability", request)

print(response.success)   # True
print(response.data)      # {"result": "Processed: Hello, NAV!"}
Step 5: Write Tests
Create tests/test_my_capability.py:

Python

import unittest

from core.contracts.capability import Request
from core.capabilities.registry import CapabilityRegistry
from core.orchestration.orchestrator import Orchestrator
from capabilities.my_capability.my_capability import MyCapability


class TestMyCapability(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = CapabilityRegistry()
        self.capability = MyCapability()
        self.registry.register(self.capability)
        self.orchestrator = Orchestrator(self.registry)

    def test_capability_properties(self) -> None:
        self.assertEqual(self.capability.name, "my_capability")
        self.assertEqual(self.capability.version, "0.1.0")

    def test_invoke_returns_response(self) -> None:
        request = Request(request_id="test_001", payload={"input": "test"})
        response = self.capability.invoke(request)
        self.assertTrue(response.success)
        self.assertEqual(response.request_id, "test_001")
        self.assertIn("result", response.data)

    def test_orchestrator_routes_to_capability(self) -> None:
        request = Request(request_id="test_002", payload={"input": "hello"})
        response = self.orchestrator.route_request("my_capability", request)
        self.assertTrue(response.success)


if __name__ == "__main__":
    unittest.main()
Run the tests:

PowerShell

python -m unittest tests.test_my_capability -v
Step 6: Verify Everything
PowerShell

ruff check .
ruff format --check .
mypy core/
python -m unittest discover -s tests -v
Checklist
 Directory created under capabilities/
 __init__.py present
 Subclasses Capability ABC
 All four abstract members implemented
 Uses get_logger(__name__)
 Returns frozen Response with matching request_id
 No vendor imports in capability code
 Registered with CapabilityRegistry
 Tests written and passing
 Ruff lint and format clean
 Documentation updated