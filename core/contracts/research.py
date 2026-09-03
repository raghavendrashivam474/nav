from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ResearchQuery:
    terms: str
    depth: str = "standard"
    sources_whitelist: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ResearchResult:
    query: str
    sources: list[dict[str, Any]]
    synthesis: str


class ResearchCapabilityInterface(ABC):
    @abstractmethod
    def perform_research(self, query: ResearchQuery) -> ResearchResult:
        pass
