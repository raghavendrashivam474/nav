"""Research capability package for NAV."""

from capabilities.research.capability import ResearchCapability
from capabilities.research.discovery import MockSearchProvider
from capabilities.research.provenance import ProvenanceTracker
from capabilities.research.retrieval import HttpxRetriever, MockRetriever, normalize_url
from capabilities.research.service import ResearchService

__all__ = [
    "ResearchCapability",
    "ResearchService",
    "MockSearchProvider",
    "HttpxRetriever",
    "MockRetriever",
    "ProvenanceTracker",
    "normalize_url",
]
