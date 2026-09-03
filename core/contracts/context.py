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
class NavContext:
    user: UserContext
    session: SessionContext
    conversation: ConversationContext
    ambient_data: dict[str, Any] = field(default_factory=dict)
