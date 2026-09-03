"""Routing data structures for the S5 Hybrid AI Layer.

These types let the ModelRouter reason about providers and requests
without coupling to any specific implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Locality(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"


class CostClass(str, Enum):
    FREE = "free"
    PAID = "paid"


class QualityClass(str, Enum):
    STANDARD = "standard"
    HIGH = "high"


@dataclass(frozen=True)
class ProviderMetadata:
    """Routing-relevant description of an AI provider."""

    name: str
    locality: Locality
    cost_class: CostClass
    quality_class: QualityClass
    latency_class: str = "variable"
    capabilities: tuple[str, ...] = ("chat",)
    available: bool = True


@dataclass(frozen=True)
class RoutingContext:
    """Structured information about what a request needs from the AI layer.

    Callers can populate fields via AIRequest.options["routing"].
    Sensible defaults ensure backward compatibility.
    """

    task_type: str = "general"
    complexity: str = "standard"
    privacy: str = "normal"
    quality_requirement: str = "standard"
    cost_preference: str = "normal"
    latency_preference: str = "normal"
    constraints: tuple[str, ...] = ()
    preferences: tuple[str, ...] = ()


@dataclass(frozen=True)
class RoutingDecision:
    """The router's output: which provider to use and why."""

    provider_name: str
    reason: str
    fallback_chain: tuple[str, ...] = ()
