"""Research context store - S10.

In-memory store for active research sessions. Separate from long-term
Memory to preserve the session/memory distinction.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from core.contracts.context import ResearchSessionContext
from core.log import get_logger

logger = get_logger(__name__)


class ResearchContextStore:
    """Thread-safe in-memory store for active research sessions."""

    def __init__(self, max_sessions: int = 50, ttl_seconds: float = 3600.0) -> None:
        self._sessions: dict[str, ResearchSessionContext] = {}
        self._timestamps: dict[str, float] = {}
        self._max_sessions = max_sessions
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def create(self, root_query: str) -> ResearchSessionContext:
        """Create a new research session and return its context."""
        session_id = f"rs_{uuid.uuid4().hex[:12]}"
        ctx = ResearchSessionContext(
            session_id=session_id,
            root_query=root_query,
            history_queries=(root_query,),
        )
        with self._lock:
            self._evict_if_needed()
            self._sessions[session_id] = ctx
            self._timestamps[session_id] = time.monotonic()
        logger.info("Created research session: %s", session_id)
        return ctx

    def get(self, session_id: str) -> ResearchSessionContext | None:
        """Retrieve an active session, or None if expired/missing."""
        with self._lock:
            if session_id not in self._sessions:
                return None
            if self._is_expired(session_id):
                del self._sessions[session_id]
                del self._timestamps[session_id]
                return None
            self._timestamps[session_id] = time.monotonic()
            return self._sessions[session_id]

    def update(self, session_id: str, **kwargs: Any) -> ResearchSessionContext | None:
        """Update session fields. Returns updated context or None."""
        with self._lock:
            if session_id not in self._sessions:
                return None
            old = self._sessions[session_id]
            data: dict[str, Any] = {
                "session_id": old.session_id,
                "root_query": old.root_query,
                "current_subtopic": old.current_subtopic,
                "depth_level": old.depth_level,
                "depth": old.depth,
                "recent_findings": old.recent_findings,
                "source_ids": old.source_ids,
                "open_questions": old.open_questions,
                "history_queries": old.history_queries,
                "metadata": dict(old.metadata),
            }
            data.update(kwargs)
            updated = ResearchSessionContext(**data)
            self._sessions[session_id] = updated
            self._timestamps[session_id] = time.monotonic()
            return updated

    def remove(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                del self._timestamps[session_id]
                return True
            return False

    def cleanup_expired(self) -> int:
        """Remove all expired sessions. Returns count removed."""
        removed = 0
        with self._lock:
            expired = [sid for sid in self._sessions if self._is_expired(sid)]
            for sid in expired:
                del self._sessions[sid]
                del self._timestamps[sid]
                removed += 1
        if removed:
            logger.info("Cleaned up %d expired research sessions", removed)
        return removed

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def _is_expired(self, session_id: str) -> bool:
        ts = self._timestamps.get(session_id, 0)
        return (time.monotonic() - ts) > self._ttl

    def _evict_if_needed(self) -> None:
        while len(self._sessions) >= self._max_sessions:
            oldest = min(self._timestamps, key=lambda k: self._timestamps[k])
            del self._sessions[oldest]
            del self._timestamps[oldest]
