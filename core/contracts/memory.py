from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MemoryRecord:
    key: str
    value: Any
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MemoryQuery:
    query_text: str | None = None
    tags: list[str] = field(default_factory=list)
    limit: int = 10


class MemoryCapabilityInterface(ABC):
    @abstractmethod
    def store(self, record: MemoryRecord) -> bool:
        pass

    @abstractmethod
    def retrieve(self, query: MemoryQuery) -> list[MemoryRecord]:
        pass
