"""Environment contracts — S21: Multi-device Foundation.

Defines the core abstractions for NAV environment, device, and runtime
identity. These contracts establish the foundation for NAV to operate
across multiple devices/runtimes while preserving identity, state
ownership, and security.

Key principles:
- Environment identity is separate from device and runtime identity.
- A device may host multiple runtimes over its lifetime.
- A runtime is an ephemeral instance; device and environment are durable.
- Identity does not imply authentication or authorization.
- State origin tracking enables future synchronization without
  implementing it prematurely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Environment Identity
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnvironmentIdentity:
    """Stable identity for a personal NAV environment.

    An environment represents the logical personal NAV instance that
    may span multiple devices and runtimes. This is the top-level
    ownership boundary for personal state.
    """

    environment_id: str
    display_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# Well-known default environment for backward compatibility.
# Used when no explicit environment is configured (S17-S20 legacy paths).
DEFAULT_ENVIRONMENT = EnvironmentIdentity(
    environment_id="nav:default",
    display_name="Default NAV Environment",
)


# ---------------------------------------------------------------------------
# Device Identity
# ---------------------------------------------------------------------------


class DevicePlatform(str, Enum):
    """Known device platform categories."""

    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    ANDROID = "android"
    IOS = "ios"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DeviceCapabilities:
    """Descriptive representation of what a device can do.

    Intentionally simple and boolean. Describes presence of
    capabilities, not their quality or configuration.
    """

    audio_input: bool = False
    audio_output: bool = False
    local_ai: bool = False
    network: bool = True
    persistent_storage: bool = True
    display: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DeviceIdentity:
    """Stable identity for a physical or logical host.

    A device persists across runtime restarts. A single device may
    host multiple runtimes over its lifetime.
    """

    device_id: str
    platform: DevicePlatform = DevicePlatform.UNKNOWN
    architecture: str = ""
    capabilities: DeviceCapabilities = field(
        default_factory=DeviceCapabilities,
    )
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Runtime Identity
# ---------------------------------------------------------------------------


class RuntimeStatus(str, Enum):
    """Lifecycle state of a NAV runtime instance."""

    STARTING = "starting"
    ACTIVE = "active"
    DETACHED = "detached"
    TERMINATED = "terminated"


@dataclass(frozen=True)
class RuntimeIdentity:
    """Identity for a specific NAV runtime instance.

    A runtime is an ephemeral process that runs on a device within
    an environment. Runtimes may restart; their identity changes
    on each start unless explicitly persisted.
    """

    runtime_id: str
    environment_id: str
    device_id: str
    started_at: str = ""
    status: RuntimeStatus = RuntimeStatus.ACTIVE
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeDescriptor:
    """Complete description of a runtime and its host device.

    Combines runtime identity with device capabilities for
    capability-aware dispatch decisions in future sprints.
    """

    runtime: RuntimeIdentity
    device: DeviceIdentity


# ---------------------------------------------------------------------------
# State Origin
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StateOrigin:
    """Provenance metadata for a piece of state.

    Records which runtime/device created or last modified a state
    element. This is the minimal foundation for future
    synchronization — it tracks origin without implementing sync.
    """

    environment_id: str
    origin_runtime_id: str = ""
    origin_device_id: str = ""
    state_version: int = 1
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
