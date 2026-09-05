"""Investigation continuity sub-package — S16.

Enables NAV to resolve and resume persistent investigations
across sessions with deterministic state reconstruction.
"""

from capabilities.research.investigation.continuity.models import (
    InvestigationContinuation,
    ResolutionMatch,
    ResolutionResult,
)
from capabilities.research.investigation.continuity.service import (
    InvestigationContinuityService,
)

__all__ = [
    "InvestigationContinuation",
    "InvestigationContinuityService",
    "ResolutionMatch",
    "ResolutionResult",
]
