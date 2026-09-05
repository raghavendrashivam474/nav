"""Investigation sub-package — S15.

Persistent research investigations that accumulate findings,
evidence, and hypotheses across multiple research interactions.
"""

from capabilities.research.investigation.models import (
    Hypothesis,
    HypothesisStatus,
    Investigation,
    InvestigationQuery,
    InvestigationStatus,
)
from capabilities.research.investigation.repository import InvestigationRepository
from capabilities.research.investigation.service import InvestigationService
from capabilities.research.investigation.sqlite_repo import (
    SQLiteInvestigationRepository,
)

__all__ = [
    "Hypothesis",
    "HypothesisStatus",
    "Investigation",
    "InvestigationQuery",
    "InvestigationStatus",
    "InvestigationRepository",
    "InvestigationService",
    "SQLiteInvestigationRepository",
]
