"""Context contracts - S1 + S10 + S12.

Defines session, user, conversation, research, and personal context models.
S10: Added ResearchSessionContext for multi-turn research continuity.
S12: Added PersonalContext models (Project, Goal, Commitment, CurrentFocus).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class UserContext:
    user_id: str
    preferences: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SessionContext:
    session_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConversationContext:
    conversation_id: str
    turns_count: int = 0
    history_summary: str | None = None


@dataclass(frozen=True)
class ResearchSessionContext:
    """Short-lived context for an active research investigation.

    Tracks the state of a multi-turn research thread so that follow-up
    requests like 'go deeper' or 'focus on X' can be resolved against
    the active investigation rather than treated as isolated queries.

    This is session-scoped volatile state, NOT long-term memory.
    """

    session_id: str
    root_query: str
    current_subtopic: str | None = None
    depth_level: int = 1
    depth: str = "standard"
    recent_findings: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    history_queries: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# S12: Personal Context Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Project:
    """An active project the user is working on."""

    project_id: str
    name: str
    status: str = "active"
    description: str = ""
    priority: int = 0
    current_focus: str = ""


@dataclass(frozen=True)
class Goal:
    """Something the user is trying to accomplish."""

    goal_id: str
    description: str
    status: str = "active"
    priority: int = 0
    project_id: str | None = None


@dataclass(frozen=True)
class Commitment:
    """Something the user has explicitly identified as mattering."""

    commitment_id: str
    description: str
    status: str = "active"


@dataclass(frozen=True)
class CurrentFocus:
    """What the user is currently focused on right now."""

    project_id: str | None = None
    goal_id: str | None = None
    activity: str = ""
    topic: str = ""


@dataclass(frozen=True)
class PersonalContext:
    """Aggregated personal context: projects, goals, commitments, focus.

    All S12 personal context is *explicit* — established directly by the
    user, not inferred.  Inference is deferred to S13/S14.
    """

    projects: tuple[Project, ...] = ()
    goals: tuple[Goal, ...] = ()
    commitments: tuple[Commitment, ...] = ()
    current_focus: CurrentFocus | None = None


# ---------------------------------------------------------------------------
# Top-level snapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NavContext:
    user: UserContext
    session: SessionContext
    conversation: ConversationContext
    ambient_data: dict[str, Any] = field(default_factory=dict)
    research: ResearchSessionContext | None = None
    personal_context: PersonalContext | None = None
