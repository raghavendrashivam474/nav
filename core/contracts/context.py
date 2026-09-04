"""Context contracts - S1 + S10.

Defines session, user, conversation, and research context models.
S10: Added ResearchSessionContext for multi-turn research continuity.
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


@dataclass(frozen=True)
class NavContext:
    user: UserContext
    session: SessionContext
    conversation: ConversationContext
    ambient_data: dict[str, Any] = field(default_factory=dict)
    research: ResearchSessionContext | None = None
