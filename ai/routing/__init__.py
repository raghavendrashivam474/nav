"""S5 Hybrid AI Layer — Model Router.

Provides policy-driven AI provider selection behind the existing AIGateway.
"""

from ai.routing.router import ModelRouter
from ai.routing.types import (
    CostClass,
    Locality,
    ProviderMetadata,
    QualityClass,
    RoutingContext,
    RoutingDecision,
)

__all__ = [
    "CostClass",
    "Locality",
    "ModelRouter",
    "ProviderMetadata",
    "QualityClass",
    "RoutingContext",
    "RoutingDecision",
]
