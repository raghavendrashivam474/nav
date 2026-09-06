"""S21: Multi-device Foundation.

Provides environment, device, and runtime identity management
for NAV's multi-device architecture foundation.
"""

from core.environment.identity import (
    create_device_identity,
    create_runtime_identity,
    detect_architecture,
    detect_platform,
    generate_device_id,
    generate_environment_id,
    generate_runtime_id,
)
from core.environment.registry import RuntimeRegistry

__all__ = [
    "RuntimeRegistry",
    "create_device_identity",
    "create_runtime_identity",
    "detect_architecture",
    "detect_platform",
    "generate_device_id",
    "generate_environment_id",
    "generate_runtime_id",
]
