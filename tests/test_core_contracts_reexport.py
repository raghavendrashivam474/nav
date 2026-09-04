"""Tests for core.contracts re-exports."""

import unittest

import core.contracts as contracts


class TestCoreContractsReexports(unittest.TestCase):
    def test_reexports_presence(self) -> None:
        expected_symbols = [
            "Capability",
            "Request",
            "Response",
            "NavContext",
            "UserContext",
            "SessionContext",
            "ConversationContext",
            "ResearchSessionContext",
            "AIGateway",
            "AIMessage",
            "AIRequest",
            "AIResponse",
            "MemoryCapabilityInterface",
            "MemoryQuery",
            "MemoryRecord",
            "ResearchCapabilityInterface",
            "ResearchQuery",
            "ResearchResult",
            "SearchProvider",
            "ContinuationIntent",
        ]
        for symbol in expected_symbols:
            self.assertTrue(
                hasattr(contracts, symbol),
                f"core.contracts missing re-export: {symbol}",
            )
