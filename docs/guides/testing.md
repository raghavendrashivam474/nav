# Guide: Testing in NAV

This guide covers testing patterns, conventions, and workflows for the NAV project.

---

## Test Framework

NAV uses Python's built-in `unittest` framework.

**Why not pytest?**
- `unittest` is in the standard library (zero dependencies).
- The current test suite is small and well-served by `unittest`.
- Migration to pytest may be evaluated in a future sprint if the test suite grows significantly.

---

## Running Tests

### All Tests

```powershell
python -m unittest discover -s tests -v
Specific Test Module
PowerShell

python -m unittest tests.test_contracts -v
python -m unittest tests.test_logging -v
Specific Test Class
PowerShell

python -m unittest tests.test_contracts.TestNAVArchitectureSkeleton -v
Specific Test Method
PowerShell

python -m unittest tests.test_contracts.TestNAVArchitectureSkeleton.test_capability_registration -v
Test File Organization
text

tests/
├── test_contracts.py       # S1: Core contract verification
├── test_logging.py         # S2: Logging foundation verification
├── test_<capability>.py    # Future: Per-capability tests
└── test_<component>.py     # Future: Per-component tests
Naming Conventions
Test files: test_<module_name>.py
Test classes: Test<DescriptiveName>(unittest.TestCase)
Test methods: test_<specific_behavior>(self)
Test Patterns
Pattern 1: Contract Verification
Verify that abstract contracts can be implemented and behave correctly.

Python

class TestContractBehavior(unittest.TestCase):
    def test_request_is_frozen(self) -> None:
        req = Request(request_id="test", payload={"key": "value"})
        with self.assertRaises(AttributeError):
            req.request_id = "modified"  # type: ignore[misc]
Pattern 2: Registry + Orchestrator Integration
Verify the full pipeline from registration to routing.

Python

class TestPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = CapabilityRegistry()
        self.registry.register(CognitionCapability())
        self.orchestrator = Orchestrator(self.registry)

    def test_end_to_end_routing(self) -> None:
        req = Request(request_id="e2e_001", payload={"prompt": "Hello"})
        res = self.orchestrator.route_request("cognition", req)
        self.assertTrue(res.success)
        self.assertEqual(res.request_id, "e2e_001")
Pattern 3: Error Handling
Verify graceful failure modes.

Python

def test_missing_capability_returns_error_response(self) -> None:
    req = Request(request_id="err_001")
    res = self.orchestrator.route_request("nonexistent", req)
    self.assertFalse(res.success)
    self.assertIsNotNone(res.error)
Pattern 4: Logging Verification
Verify that logging infrastructure works correctly.

Python

def test_logger_configuration(self) -> None:
    logger = get_logger("test.module")
    self.assertIsInstance(logger, logging.Logger)
    self.assertEqual(logger.level, logging.INFO)
    self.assertGreater(len(logger.handlers), 0)
Writing Good Tests
Do
Test behavior, not implementation. Focus on inputs and outputs.
Use descriptive test names. test_duplicate_registration_raises_error is better than test_registry_2.
Keep tests independent. Each test should work in isolation.
Use setUp() for shared fixtures. Avoid repeating setup code.
Test the happy path AND error paths. Both matter.
Assert specific values. self.assertEqual(x, 42) is better than self.assertTrue(x).
Don't
Don't test private methods directly. Test through the public interface.
Don't rely on test execution order. Tests may run in any order.
Don't mock everything. Use real objects when the real object is fast and deterministic.
Don't skip failing tests. Fix them or document the known issue.
Don't add external service dependencies to unit tests. Integration tests are separate.
Integration Tests (Future)
When NAV integrates real AI providers, databases, or external services, integration tests should:

Live in a separate directory: tests/integration/
Be skippable via environment variable: NAV_SKIP_INTEGRATION=1
Use real credentials from .env, never hardcoded
Be clearly marked with a naming convention: test_integration_*.py
Example skip pattern:

Python

import os
import unittest

@unittest.skipIf(
    os.environ.get("NAV_SKIP_INTEGRATION"),
    "Integration tests disabled",
)
class TestOpenAIIntegration(unittest.TestCase):
    ...
CI Testing (Future)
When CI is established (planned for S3 or S4), the test pipeline should run:

PowerShell

# Fast checks first
ruff check .
ruff format --check .
mypy core/

# Unit tests
python -m unittest discover -s tests -v

# Integration tests (optional, with credentials)
python -m unittest discover -s tests/integration -v
Test Coverage
NAV does not currently enforce a coverage threshold. As the codebase grows, consider adding coverage.py to the dev dependencies:

toml

[project.optional-dependencies]
dev = [
    "ruff>=0.4.0",
    "mypy>=1.10.0",
    "coverage>=7.0.0",
]
Usage:

PowerShell

coverage run -m unittest discover -s tests
coverage report -m
Quick Reference
Task    Command
Run all tests    python -m unittest discover -s tests -v
Run one module    python -m unittest tests.test_contracts -v
Run one test    python -m unittest tests.test_contracts.TestNAVArchitectureSkeleton.test_capability_registration -v
Lint + format + type check    ruff check . && ruff format --check . && mypy core/
Full verification    All of the above