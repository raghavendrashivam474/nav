from abc import ABC, abstractmethod
from typing import Any, Dict
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Request:
    request_id: str
    payload: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class Response:
    request_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: str | None = None

class Capability(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def invoke(self, request: Request) -> Response:
        pass
