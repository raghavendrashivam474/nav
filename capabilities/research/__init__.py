"""Research capability package for NAV — S7 + S8 + S15."""

from capabilities.research.capability import ResearchCapability
from capabilities.research.concurrency import (
    RetrievalOutcome,
    retrieve_concurrently,
)
from capabilities.research.discovery import MockSearchProvider
from capabilities.research.investigation import (
    Hypothesis,
    HypothesisStatus,
    Investigation,
    InvestigationQuery,
    InvestigationService,
    InvestigationStatus,
    SQLiteInvestigationRepository,
)
from capabilities.research.progress import (
    CollectingProgressReporter,
    LoggingProgressReporter,
    NullProgressReporter,
    ProgressEvent,
    ProgressReporter,
    ProgressStage,
)
from capabilities.research.provenance import ProvenanceTracker
from capabilities.research.retrieval import (
    HttpxRetriever,
    MockRetriever,
    normalize_url,
)
from capabilities.research.security import (
    build_safe_extraction_prompt,
    build_safe_synthesis_prompt,
    validate_ai_output,
    wrap_untrusted_content,
)
from capabilities.research.service import ResearchService

__all__ = [
    "ResearchCapability",
    "ResearchService",
    "MockSearchProvider",
    "HttpxRetriever",
    "MockRetriever",
    "ProvenanceTracker",
    "normalize_url",
    "RetrievalOutcome",
    "retrieve_concurrently",
    "ProgressEvent",
    "ProgressStage",
    "ProgressReporter",
    "NullProgressReporter",
    "LoggingProgressReporter",
    "CollectingProgressReporter",
    "wrap_untrusted_content",
    "build_safe_extraction_prompt",
    "build_safe_synthesis_prompt",
    "validate_ai_output",
    # S15
    "Investigation",
    "InvestigationStatus",
    "InvestigationQuery",
    "InvestigationService",
    "SQLiteInvestigationRepository",
    "Hypothesis",
    "HypothesisStatus",
]
