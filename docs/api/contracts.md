# NAV v0 — Contract Reference

This document provides a complete reference for all typed contracts in NAV. These contracts define the stable interfaces that all capabilities, providers, and components must implement.

> **Architectural Principle:** Stable contracts over stable implementations. Core depends on these interfaces, never on specific vendors or technologies.

---

## 1. Capability Contract

**Module:** `core.contracts.capability`

### `Request`

Immutable request object passed to all capabilities.

```python
@dataclass(frozen=True)
class Request:
    request_id: str
    payload: dict[str, Any] = field(default_factory=dict)
Field    Type    Description
request_id    str    Unique identifier for this request
payload    dict[str, Any]    Arbitrary key-value data for the capability
Response
Immutable response object returned by all capabilities.

Python

@dataclass(frozen=True)
class Response:
    request_id: str
    data: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: str | None = None
Field    Type    Description
request_id    str    Must match the originating Request.request_id
data    dict[str, Any]    Response payload
success    bool    Whether the operation succeeded
error    str | None    Error message if success is False
Capability (Abstract Base Class)
All capabilities must implement this interface.

Python

class Capability(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def version(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    def invoke(self, request: Request) -> Response: ...
Member    Type    Description
name    str    Unique capability identifier (e.g., "cognition")
version    str    Semantic version string
description    str    Human-readable description
invoke(request)    Response    Execute the capability and return a response
2. Context Contract
Module: core.contracts.context

UserContext
Python

@dataclass(frozen=True)
class UserContext:
    user_id: str
    preferences: dict[str, Any] = field(default_factory=dict)
SessionContext
Python

@dataclass(frozen=True)
class SessionContext:
    session_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
ConversationContext
Python

@dataclass(frozen=True)
class ConversationContext:
    conversation_id: str
    turn_count: int = 0
    history: tuple = ()
Note: history is a tuple (immutable) to preserve the frozen dataclass contract.

NavContext
Composite context aggregating all context layers.

Python

@dataclass(frozen=True)
class NavContext:
    user: UserContext
    session: SessionContext
    conversation: ConversationContext
    ambient_data: dict[str, Any] = field(default_factory=dict)
3. AI Contract
Module: core.contracts.ai

AIMessage
Python

@dataclass(frozen=True)
class AIMessage:
    role: str
    content: str
Field    Type    Description
role    str    Message role: "system", "user", "assistant"
content    str    Message text content
AIRequest
Python

@dataclass(frozen=True)
class AIRequest:
    messages: list[AIMessage]
    temperature: float = 0.7
    max_tokens: int | None = None
    options: dict[str, Any] = field(default_factory=dict)
AIResponse
Python

@dataclass(frozen=True)
class AIResponse:
    content: str
    model_used: str
    usage: dict[str, int] = field(default_factory=dict)
    raw_response: Any | None = None
AIGateway (Abstract Base Class)
Uniform invocation interface for all AI providers.

Python

class AIGateway(ABC):
    @abstractmethod
    def invoke(self, request: AIRequest) -> AIResponse: ...
4. Memory Contract
Module: core.contracts.memory

MemoryRecord
Python

@dataclass(frozen=True)
class MemoryRecord:
    key: str
    value: Any
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
MemoryQuery
Python

@dataclass(frozen=True)
class MemoryQuery:
    query_text: str | None = None
    tags: list[str] = field(default_factory=list)
    limit: int = 10
MemoryCapabilityInterface (Abstract Base Class)
Python

class MemoryCapabilityInterface(ABC):
    @abstractmethod
    def store(self, record: MemoryRecord) -> None: ...

    @abstractmethod
    def retrieve(self, query: MemoryQuery) -> list[MemoryRecord]: ...
5. Research Contract
Module: core.contracts.research

ResearchQuery
Python

@dataclass(frozen=True)
class ResearchQuery:
    terms: str
    depth: str = "standard"
    sources_whitelist: list[str] = field(default_factory=list)
ResearchResult
Python

@dataclass(frozen=True)
class ResearchResult:
    query: str
    sources: list[dict[str, Any]]
    synthesis: str
ResearchCapabilityInterface (Abstract Base Class)
Python

class ResearchCapabilityInterface(ABC):
    @abstractmethod
    def research(self, query: ResearchQuery) -> ResearchResult: ...
6. Infrastructure Contracts
CapabilityRegistry
Module: core.capabilities.registry

Python

class CapabilityRegistry:
    def register(self, capability: Capability) -> None: ...
    def get(self, name: str) -> Capability: ...
    def list_capabilities(self) -> list[str]: ...
Method    Description
register(capability)    Register a capability. Raises ValueError on duplicate name.
get(name)    Retrieve a capability by name. Raises KeyError if not found.
list_capabilities()    Return a list of all registered capability names.
Orchestrator
Module: core.orchestration.orchestrator

Python

class Orchestrator:
    def __init__(self, registry: CapabilityRegistry) -> None: ...
    def route_request(self, target_capability: str, request: Request) -> Response: ...
Method    Description
route_request(target, request)    Route a request to the named capability. Returns error Response on failure.
get_logger
Module: core.log

Python

def get_logger(name: str, level: int = logging.INFO) -> logging.Logger: ...
Returns a configured logging.Logger with consistent formatting. Use get_logger(__name__) in all modules.

Contract Invariants
All data types are frozen. No mutation after creation.
All fields are typed. No untyped Any at the top level (nested dict[str, Any] is acceptable for extensibility).
No vendor leakage. Contracts reference no external packages.
Backward compatible. Adding optional fields with defaults is allowed. Removing or renaming fields is a breaking change.
Testable in isolation. Every contract can be instantiated and verified without external services.