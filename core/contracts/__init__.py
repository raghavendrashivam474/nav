"""Core contracts for NAV.

Exposes stable abstract base classes, dataclasses, protocols, and enums
defining the boundaries between Core, Capabilities, AI infrastructure,
and Storage/Provider layers.
"""

from core.contracts.ai import (
    AIGateway,
    AIMessage,
    AIRequest,
    AIResponse,
)
from core.contracts.capability import (
    Capability,
    Request,
    Response,
)
from core.contracts.context import (
    Commitment,
    ConversationContext,
    CurrentFocus,
    Goal,
    NavContext,
    PersonalContext,
    Project,
    ResearchSessionContext,
    SessionContext,
    UserContext,
)
from core.contracts.memory import (
    MemoryCapabilityInterface,
    MemoryQuery,
    MemoryRecord,
)
from core.contracts.research import (
    ContinuationIntent,
    ResearchCapabilityInterface,
    ResearchEvidence,
    ResearchFinding,
    ResearchQuery,
    ResearchResult,
    ResearchSource,
    RetrievedContent,
    SearchProvider,
    SourceCandidate,
    SourceRetriever,
    SourceStatus,
    SourceType,
    SupportState,
)

__all__ = [
    # Capability & Invocation
    "Capability",
    "Request",
    "Response",
    # Context
    "NavContext",
    "UserContext",
    "SessionContext",
    "ConversationContext",
    "ResearchSessionContext",
    "Project",
    "Goal",
    "Commitment",
    "CurrentFocus",
    "PersonalContext",
    # AI Layer
    "AIGateway",
    "AIMessage",
    "AIRequest",
    "AIResponse",
    # Memory
    "MemoryCapabilityInterface",
    "MemoryQuery",
    "MemoryRecord",
    # Research
    "ContinuationIntent",
    "ResearchCapabilityInterface",
    "ResearchEvidence",
    "ResearchFinding",
    "ResearchQuery",
    "ResearchResult",
    "ResearchSource",
    "RetrievedContent",
    "SearchProvider",
    "SourceCandidate",
    "SourceRetriever",
    "SourceStatus",
    "SourceType",
    "SupportState",
]
