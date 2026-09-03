from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass(frozen=True)
class ResearchQuery:
    terms: str
    depth: str = 'standard'
    sources_whitelist: List[str] = field(default_factory=list)

@dataclass(frozen=True)
class ResearchResult:
    query: str
    sources: List[Dict[str, Any]]
    synthesis: str

class ResearchCapabilityInterface(ABC):
    @abstractmethod
    def perform_research(self, query: ResearchQuery) -> ResearchResult:
        pass
