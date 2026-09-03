from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass(frozen=True)
class MemoryRecord:
    key: str
    value: Any
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class MemoryQuery:
    query_text: str | None = None
    tags: List[str] = field(default_factory=list)
    limit: int = 10

class MemoryCapabilityInterface(ABC):
    @abstractmethod
    def store(self, record: MemoryRecord) -> bool:
        pass

    @abstractmethod
    def retrieve(self, query: MemoryQuery) -> List[MemoryRecord]:
        pass
