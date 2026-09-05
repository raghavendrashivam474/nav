"""Investigation sub-package — S15 + S16.

Persistent research investigations that accumulate findings,
evidence, and hypotheses across multiple research interactions.

S16: Added ActivityType, InvestigationActivity, and the
continuity sub-package for cross-session resumption.
"""

from capabilities.research.investigation.models import (
    ActivityType,
    Hypothesis,
    HypothesisStatus,
    Investigation,
    InvestigationActivity,
    InvestigationQuery,
    InvestigationStatus,
)
from capabilities.research.investigation.repository import InvestigationRepository
from capabilities.research.investigation.service import InvestigationService
from capabilities.research.investigation.sqlite_repo import (
    SQLiteInvestigationRepository,
)

__all__ = [
    "ActivityType",
    "Hypothesis",
    "HypothesisStatus",
    "Investigation",
    "InvestigationActivity",
    "InvestigationQuery",
    "InvestigationStatus",
    "InvestigationRepository",
    "InvestigationService",
    "SQLiteInvestigationRepository",
]
