"""Core contracts for NAV.

Exposes stable abstract base classes, dataclasses, protocols, and enums
defining the boundaries between Core, Capabilities, AI infrastructure,
Storage/Provider layers, Technical Intelligence/Work, Security,
Environment, and Findings.
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
from core.contracts.environment import (
    DEFAULT_ENVIRONMENT,
    DeviceCapabilities,
    DeviceIdentity,
    DevicePlatform,
    EnvironmentIdentity,
    RuntimeDescriptor,
    RuntimeIdentity,
    RuntimeStatus,
    StateOrigin,
)
from core.contracts.finding import (
    Finding,
    FindingState,
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
from core.contracts.security import (
    SYSTEM_ACTOR,
    ActorIdentity,
    ActorType,
    AuthorizationDecision,
    AuthorizationOutcome,
    AuthorizationRequest,
    SecurityEvent,
    SecurityEventType,
)
from core.contracts.work import (
    PlannerProtocol,
    StepEvaluatorProtocol,
    StepStatus,
    Work,
    WorkActivity,
    WorkActivityType,
    WorkCapabilityInterface,
    WorkPlan,
    WorkQuery,
    WorkStatus,
    WorkStep,
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
    # Environment (S21)
    "DEFAULT_ENVIRONMENT",
    "DeviceCapabilities",
    "DeviceIdentity",
    "DevicePlatform",
    "EnvironmentIdentity",
    "RuntimeDescriptor",
    "RuntimeIdentity",
    "RuntimeStatus",
    "StateOrigin",
    # Finding (S25)
    "Finding",
    "FindingState",
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
    # Security (S20)
    "ActorIdentity",
    "ActorType",
    "AuthorizationDecision",
    "AuthorizationOutcome",
    "AuthorizationRequest",
    "SecurityEvent",
    "SecurityEventType",
    "SYSTEM_ACTOR",
    # Work & Technical Intelligence (S17)
    "Work",
    "WorkPlan",
    "WorkStep",
    "WorkStatus",
    "StepStatus",
    "WorkActivity",
    "WorkActivityType",
    "WorkQuery",
    "PlannerProtocol",
    "StepEvaluatorProtocol",
    "WorkCapabilityInterface",
]
