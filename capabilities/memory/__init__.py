"""NAV Memory capability — S6 persistent memory + S13 intelligence."""

from capabilities.memory.capability import MemoryCapability
from capabilities.memory.repository import MemoryRepository
from capabilities.memory.semantics import (
    Confidence,
    Importance,
    LifecycleStatus,
    MemoryType,
    apply_defaults,
)
from capabilities.memory.service import MemoryService
from capabilities.memory.sqlite_repo import SQLiteMemoryRepository

__all__ = [
    "MemoryCapability",
    "MemoryRepository",
    "MemoryService",
    "SQLiteMemoryRepository",
    # S13 semantics
    "MemoryType",
    "Importance",
    "Confidence",
    "LifecycleStatus",
    "apply_defaults",
]
