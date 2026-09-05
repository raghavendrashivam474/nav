"""Memory intelligence semantics — S13.

Defines the typed vocabulary for memory classification, importance,
confidence/provenance, and lifecycle status.  Stored in the existing
MemoryRecord.metadata dict under well-known keys, preserving full
backward compatibility with the frozen MemoryRecord contract.
"""

from __future__ import annotations

from enum import Enum

# ---------------------------------------------------------------------------
# Well-known metadata keys
# ---------------------------------------------------------------------------

META_TYPE = "memory_type"
META_IMPORTANCE = "importance"
META_CONFIDENCE = "confidence"
META_PROVENANCE = "provenance"
META_LIFECYCLE = "lifecycle_status"
META_VALID_FROM = "valid_from"
META_VALID_UNTIL = "valid_until"
META_SUPERSEDED_BY = "superseded_by"
META_SUPERSEDES = "supersedes"


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

class MemoryType(str, Enum):
    """What kind of information this memory represents.

    Kept deliberately small.  Each type must justify its existence by
    requiring *different treatment* in retrieval or lifecycle.
    """

    FACT = "fact"
    PREFERENCE = "preference"
    DECISION = "decision"
    GOAL = "goal"
    COMMITMENT = "commitment"
    OBSERVATION = "observation"
    INSTRUCTION = "instruction"
    TEMPORARY = "temporary"


# ---------------------------------------------------------------------------
# Importance
# ---------------------------------------------------------------------------

class Importance(str, Enum):
    """How much NAV should care about this memory."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


IMPORTANCE_RANK: dict[str, int] = {
    Importance.LOW.value: 1,
    Importance.NORMAL.value: 2,
    Importance.HIGH.value: 3,
    Importance.CRITICAL.value: 4,
}


# ---------------------------------------------------------------------------
# Confidence / Provenance
# ---------------------------------------------------------------------------

class Confidence(str, Enum):
    """How NAV came to know this information.

    Critical rule: NAV must never silently turn an inference into a fact.
    """

    EXPLICIT = "explicit"
    INFERRED = "inferred"
    OBSERVED = "observed"
    IMPORTED = "imported"
    SYSTEM = "system"


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

class LifecycleStatus(str, Enum):
    """Where this memory is in its lifecycle."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_TYPE = MemoryType.FACT.value
DEFAULT_IMPORTANCE = Importance.NORMAL.value
DEFAULT_CONFIDENCE = Confidence.EXPLICIT.value
DEFAULT_LIFECYCLE = LifecycleStatus.ACTIVE.value


def apply_defaults(metadata: dict) -> dict:
    """Return a copy of *metadata* with all S13 semantic keys populated.

    Existing values are preserved; only missing keys receive defaults.
    """
    meta = dict(metadata)
    meta.setdefault(META_TYPE, DEFAULT_TYPE)
    meta.setdefault(META_IMPORTANCE, DEFAULT_IMPORTANCE)
    meta.setdefault(META_CONFIDENCE, DEFAULT_CONFIDENCE)
    meta.setdefault(META_LIFECYCLE, DEFAULT_LIFECYCLE)
    meta.setdefault(META_PROVENANCE, "")
    return meta
