"""Security event log — S20.

Provides operational traceability for security decisions.
"""

from __future__ import annotations

from core.contracts.security import SecurityEvent


class SecurityEventLog:
    """In-memory security event log for observability.

    Records all security decisions for audit and debugging.
    In a future sprint, this could be backed by persistent storage.
    """

    def __init__(self, max_events: int = 10000) -> None:
        self._events: list[SecurityEvent] = []
        self._max_events = max_events

    def record(self, event: SecurityEvent) -> None:
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events :]

    def get_events(
        self, limit: int = 100, event_type: str | None = None
    ) -> list[SecurityEvent]:
        events = self._events
        if event_type:
            events = [e for e in events if e.event_type.value == event_type]
        return events[-limit:]

    @property
    def count(self) -> int:
        return len(self._events)

    def clear(self) -> None:
        self._events.clear()
