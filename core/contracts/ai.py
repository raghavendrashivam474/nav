from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass(frozen=True)
class AIMessage:
    role: str
    content: str

@dataclass(frozen=True)
class AIRequest:
    messages: List[AIMessage]
    temperature: float = 0.7
    max_tokens: int | None = None
    options: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class AIResponse:
    content: str
    model_used: str
    usage: Dict[str, int] = field(default_factory=dict)
    raw_response: Any | None = None

class AIGateway(ABC):
    @abstractmethod
    def generate(self, request: AIRequest) -> AIResponse:
        pass
