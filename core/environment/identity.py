"""Identity generation helpers — S21.

Provides deterministic identity creation for environments, devices,
and runtimes. Uses UUID4 for uniqueness by default.
"""

from __future__ import annotations

import platform
import uuid
from datetime import datetime, timezone

from core.contracts.environment import (
    DeviceCapabilities,
    DeviceIdentity,
    DevicePlatform,
    RuntimeIdentity,
    RuntimeStatus,
)


def generate_environment_id() -> str:
    """Generate a unique environment identifier."""
    return f"nav-env-{uuid.uuid4().hex[:12]}"


def generate_device_id() -> str:
    """Generate a unique device identifier."""
    return f"nav-device-{uuid.uuid4().hex[:12]}"


def generate_runtime_id() -> str:
    """Generate a unique runtime instance identifier."""
    return f"nav-runtime-{uuid.uuid4().hex[:12]}"


def detect_platform() -> DevicePlatform:
    """Detect the current device platform."""
    system = platform.system().lower()
    mapping = {
        "windows": DevicePlatform.WINDOWS,
        "linux": DevicePlatform.LINUX,
        "darwin": DevicePlatform.MACOS,
    }
    return mapping.get(system, DevicePlatform.UNKNOWN)


def detect_architecture() -> str:
    """Detect the current CPU architecture."""
    return platform.machine()


def create_device_identity(
    device_id: str | None = None,
    capabilities: DeviceCapabilities | None = None,
) -> DeviceIdentity:
    """Create a DeviceIdentity with auto-detected platform info."""
    return DeviceIdentity(
        device_id=device_id or generate_device_id(),
        platform=detect_platform(),
        architecture=detect_architecture(),
        capabilities=capabilities or DeviceCapabilities(),
    )


def create_runtime_identity(
    environment_id: str,
    device_id: str,
    runtime_id: str | None = None,
) -> RuntimeIdentity:
    """Create a RuntimeIdentity for the current process."""
    return RuntimeIdentity(
        runtime_id=runtime_id or generate_runtime_id(),
        environment_id=environment_id,
        device_id=device_id,
        started_at=datetime.now(timezone.utc).isoformat(),
        status=RuntimeStatus.ACTIVE,
    )
