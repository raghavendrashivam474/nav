"""Progress reporting abstraction for long-running operations — S8.

Provides structured, decoupled progress events and reporter protocols.
Research and other capabilities report lifecycle progress without
knowing whether the consumer is Voice, CLI, Web, or a test harness.

Invariant 3: Research does not know which interface is displaying progress.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

from core.contracts.research import utcnow
from core.log import get_logger

logger = get_logger(__name__)


class ProgressStage(str, Enum):
    """Standard lifecycle stages for long-running operations."""

    STARTED = "started"
    DISCOVERY = "discovery"
    RETRIEVAL = "retrieval"
    EXTRACTION = "extraction"
    SYNTHESIS = "synthesis"
    PERSISTENCE = "persistence"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class ProgressEvent:
    """Structured progress notification emitted during capability execution.

    Lightweight, serializable, and interface-agnostic.
    """

    stage: ProgressStage
    message: str
    completed: int = 0
    total: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utcnow)

    @property
    def percent(self) -> float:
        if self.total <= 0:
            return 0.0
        return min(100.0, round((self.completed / self.total) * 100.0, 1))

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "message": self.message,
            "completed": self.completed,
            "total": self.total,
            "percent": self.percent,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class ProgressReporter(Protocol):
    """Protocol for receiving progress events."""

    def report(self, event: ProgressEvent) -> None: ...


class NullProgressReporter:
    """Default no-op reporter when no listener is attached."""

    def report(self, event: ProgressEvent) -> None:
        pass


class LoggingProgressReporter:
    """Reporter that logs structured progress events to the NAV logger."""

    def __init__(self, logger_name: str = "NAV.Progress") -> None:
        self._logger = get_logger(logger_name)

    def report(self, event: ProgressEvent) -> None:
        if event.total > 0:
            self._logger.info(
                "[%s] %s (%d/%d, %.0f%%)",
                event.stage.value.upper(),
                event.message,
                event.completed,
                event.total,
                event.percent,
            )
        else:
            self._logger.info("[%s] %s", event.stage.value.upper(), event.message)


class CollectingProgressReporter:
    """Reporter for tests and CLI summaries that collects all events."""

    def __init__(self, on_event: Callable[[ProgressEvent], None] | None = None) -> None:
        self.events: list[ProgressEvent] = []
        self._on_event = on_event

    def report(self, event: ProgressEvent) -> None:
        self.events.append(event)
        if self._on_event is not None:
            self._on_event(event)

    def stages(self) -> list[ProgressStage]:
        return [e.stage for e in self.events]

    def clear(self) -> None:
        self.events.clear()
