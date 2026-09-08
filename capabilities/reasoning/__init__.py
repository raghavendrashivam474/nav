"""
NAV v2 — S27: Reasoning Subsystem.

Provides explicit, inspectable, and traceable structured reasoning over
S24 Evidence, S25 Findings, and S26 Comparisons.
"""

from capabilities.reasoning.capability import ReasoningCapability
from capabilities.reasoning.engine import ReasoningEngine
from capabilities.reasoning.service import ReasoningService

__all__ = [
    "ReasoningCapability",
    "ReasoningEngine",
    "ReasoningService",
]
