"""
NAV v2 — S24/S25: Evidence Subsystem.

Provides evidence representation, evaluation, traceability, and synthesis
for information acquired through S23 External Information Capability.
"""

from capabilities.evidence.service import EvidenceService
from capabilities.evidence.synthesis import EvidenceSynthesizer

__all__ = ["EvidenceService", "EvidenceSynthesizer"]
