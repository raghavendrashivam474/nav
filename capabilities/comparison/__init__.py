"""
NAV v2 — S26: Comparison Subsystem.

Provides explicit, traceable, evidence-aware comparative intelligence
across Findings, Evidence, claims, and alternatives.
"""

from capabilities.comparison.capability import ComparisonCapability
from capabilities.comparison.engine import ComparisonEngine
from capabilities.comparison.service import ComparisonService

__all__ = [
    "ComparisonCapability",
    "ComparisonEngine",
    "ComparisonService",
]
