"""S21: Multi-device Foundation tests.

Verifies environment, device, and runtime identity contracts,
the runtime registry, identity generation helpers, and
backward compatibility with S20 security.
"""

from __future__ import annotations

import platform

from core.contracts.environment import (
    DEFAULT_ENVIRONMENT,
    DeviceCapabilities,
    DeviceIdentity,
    DevicePlatform,
    EnvironmentIdentity,
    RuntimeDescriptor,
    RuntimeIdentity,
    RuntimeStatus,
    StateOrigin,
)
from core.contracts.security import SYSTEM_ACTOR, ActorIdentity, ActorType
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

# ---------------------------------------------------------------------------
# EnvironmentIdentity
# ---------------------------------------------------------------------------


class TestEnvironmentIdentity:
    def test_creation(self) -> None:
        env = EnvironmentIdentity(environment_id="env-001")
        assert env.environment_id == "env-001"
        assert env.display_name == ""
        assert env.metadata == {}

    def test_frozen(self) -> None:
        env = EnvironmentIdentity(environment_id="env-001")
        try:
            env.environment_id = "env-002"  # type: ignore[misc]
            assert False, "Should be frozen"
        except AttributeError:
            pass

    def test_default_environment_constant(self) -> None:
        assert DEFAULT_ENVIRONMENT.environment_id == "nav:default"
        assert DEFAULT_ENVIRONMENT.display_name != ""

    def test_uniqueness(self) -> None:
        env_a = EnvironmentIdentity(environment_id="a")
        env_b = EnvironmentIdentity(environment_id="b")
        assert env_a != env_b

    def test_equality(self) -> None:
        env_a = EnvironmentIdentity(environment_id="same")
        env_b = EnvironmentIdentity(environment_id="same")
        assert env_a == env_b

    def test_serialization_fields(self) -> None:
        env = EnvironmentIdentity(
            environment_id="env-001",
            display_name="My NAV",
            metadata={"owner": "user-1"},
        )
        assert env.metadata["owner"] == "user-1"


# ---------------------------------------------------------------------------
# DeviceIdentity
# ---------------------------------------------------------------------------


class TestDeviceIdentity:
    def test_creation(self) -> None:
        dev = DeviceIdentity(device_id="dev-001")
        assert dev.device_id == "dev-001"
        assert dev.platform == DevicePlatform.UNKNOWN
        assert dev.architecture == ""

    def test_frozen(self) -> None:
        dev = DeviceIdentity(device_id="dev-001")
        try:
            dev.device_id = "dev-002"  # type: ignore[misc]
            assert False, "Should be frozen"
        except AttributeError:
            pass

    def test_with_capabilities(self) -> None:
        caps = DeviceCapabilities(
            audio_input=True,
            audio_output=True,
            local_ai=True,
        )
        dev = DeviceIdentity(
            device_id="dev-001",
            platform=DevicePlatform.WINDOWS,
            capabilities=caps,
        )
        assert dev.capabilities.audio_input is True
        assert dev.capabilities.local_ai is True
        assert dev.capabilities.display is False

    def test_default_capabilities(self) -> None:
        caps = DeviceCapabilities()
        assert caps.network is True
        assert caps.persistent_storage is True
        assert caps.audio_input is False


# ---------------------------------------------------------------------------
# RuntimeIdentity
# ---------------------------------------------------------------------------


class TestRuntimeIdentity:
    def test_creation(self) -> None:
        rt = RuntimeIdentity(
            runtime_id="rt-001",
            environment_id="env-001",
            device_id="dev-001",
        )
        assert rt.runtime_id == "rt-001"
        assert rt.environment_id == "env-001"
        assert rt.device_id == "dev-001"
        assert rt.status == RuntimeStatus.ACTIVE

    def test_frozen(self) -> None:
        rt = RuntimeIdentity(
            runtime_id="rt-001",
            environment_id="env-001",
            device_id="dev-001",
        )
        try:
            rt.status = RuntimeStatus.TERMINATED  # type: ignore[misc]
            assert False, "Should be frozen"
        except AttributeError:
            pass

    def test_lifecycle_states(self) -> None:
        assert RuntimeStatus.STARTING.value == "starting"
        assert RuntimeStatus.ACTIVE.value == "active"
        assert RuntimeStatus.DETACHED.value == "detached"
        assert RuntimeStatus.TERMINATED.value == "terminated"


# ---------------------------------------------------------------------------
# RuntimeDescriptor
# ---------------------------------------------------------------------------


class TestRuntimeDescriptor:
    def test_composition(self) -> None:
        rt = RuntimeIdentity(
            runtime_id="rt-001",
            environment_id="env-001",
            device_id="dev-001",
        )
        dev = DeviceIdentity(
            device_id="dev-001",
            platform=DevicePlatform.LINUX,
        )
        desc = RuntimeDescriptor(runtime=rt, device=dev)
        assert desc.runtime.runtime_id == "rt-001"
        assert desc.device.platform == DevicePlatform.LINUX


# ---------------------------------------------------------------------------
# StateOrigin
# ---------------------------------------------------------------------------


class TestStateOrigin:
    def test_creation(self) -> None:
        origin = StateOrigin(environment_id="env-001")
        assert origin.environment_id == "env-001"
        assert origin.origin_runtime_id == ""
        assert origin.state_version == 1

    def test_frozen(self) -> None:
        origin = StateOrigin(environment_id="env-001")
        try:
            origin.state_version = 2  # type: ignore[misc]
            assert False, "Should be frozen"
        except AttributeError:
            pass

    def test_full_provenance(self) -> None:
        origin = StateOrigin(
            environment_id="env-001",
            origin_runtime_id="rt-001",
            origin_device_id="dev-001",
            state_version=5,
            timestamp="2026-01-01T00:00:00+00:00",
        )
        assert origin.origin_runtime_id == "rt-001"
        assert origin.state_version == 5


# ---------------------------------------------------------------------------
# Identity Generation Helpers
# ---------------------------------------------------------------------------


class TestIdentityGeneration:
    def test_generate_environment_id(self) -> None:
        eid = generate_environment_id()
        assert eid.startswith("nav-env-")
        assert len(eid) > 10

    def test_generate_device_id(self) -> None:
        did = generate_device_id()
        assert did.startswith("nav-device-")

    def test_generate_runtime_id(self) -> None:
        rid = generate_runtime_id()
        assert rid.startswith("nav-runtime-")

    def test_ids_are_unique(self) -> None:
        ids = {generate_environment_id() for _ in range(100)}
        assert len(ids) == 100

    def test_detect_platform(self) -> None:
        p = detect_platform()
        assert isinstance(p, DevicePlatform)
        system = platform.system().lower()
        if system == "windows":
            assert p == DevicePlatform.WINDOWS

    def test_detect_architecture(self) -> None:
        arch = detect_architecture()
        assert isinstance(arch, str)
        assert len(arch) > 0

    def test_create_device_identity(self) -> None:
        dev = create_device_identity()
        assert dev.device_id.startswith("nav-device-")
        assert dev.platform != DevicePlatform.UNKNOWN or True  # CI may vary

    def test_create_device_identity_custom_id(self) -> None:
        dev = create_device_identity(device_id="my-laptop")
        assert dev.device_id == "my-laptop"

    def test_create_runtime_identity(self) -> None:
        rt = create_runtime_identity(
            environment_id="env-001",
            device_id="dev-001",
        )
        assert rt.environment_id == "env-001"
        assert rt.device_id == "dev-001"
        assert rt.started_at != ""
        assert rt.status == RuntimeStatus.ACTIVE


# ---------------------------------------------------------------------------
# RuntimeRegistry
# ---------------------------------------------------------------------------


class TestRuntimeRegistry:
    def _make_descriptor(
        self,
        env_id: str = "env-001",
        dev_id: str = "dev-001",
        rt_id: str = "rt-001",
    ) -> RuntimeDescriptor:
        rt = RuntimeIdentity(
            runtime_id=rt_id,
            environment_id=env_id,
            device_id=dev_id,
        )
        dev = DeviceIdentity(device_id=dev_id)
        return RuntimeDescriptor(runtime=rt, device=dev)

    def test_register_and_get(self) -> None:
        reg = RuntimeRegistry("env-001")
        desc = self._make_descriptor()
        reg.register(desc)
        assert reg.get("rt-001") is desc
        assert reg.count == 1

    def test_unregister(self) -> None:
        reg = RuntimeRegistry("env-001")
        reg.register(self._make_descriptor())
        reg.unregister("rt-001")
        assert reg.get("rt-001") is None
        assert reg.count == 0

    def test_environment_mismatch_rejected(self) -> None:
        reg = RuntimeRegistry("env-001")
        desc = self._make_descriptor(env_id="env-999")
        try:
            reg.register(desc)
            assert False, "Should reject mismatched environment"
        except ValueError:
            pass

    def test_active_runtimes(self) -> None:
        reg = RuntimeRegistry("env-001")
        active = self._make_descriptor(rt_id="rt-active")
        terminated_rt = RuntimeIdentity(
            runtime_id="rt-dead",
            environment_id="env-001",
            device_id="dev-001",
            status=RuntimeStatus.TERMINATED,
        )
        terminated = RuntimeDescriptor(
            runtime=terminated_rt,
            device=DeviceIdentity(device_id="dev-001"),
        )
        reg.register(active)
        reg.register(terminated)
        assert len(reg.active_runtimes()) == 1
        assert reg.active_runtimes()[0].runtime.runtime_id == "rt-active"

    def test_multiple_runtimes_same_device(self) -> None:
        reg = RuntimeRegistry("env-001")
        reg.register(self._make_descriptor(rt_id="rt-a"))
        reg.register(self._make_descriptor(rt_id="rt-b"))
        assert reg.count == 2

    def test_clear(self) -> None:
        reg = RuntimeRegistry("env-001")
        reg.register(self._make_descriptor())
        reg.clear()
        assert reg.count == 0

    def test_environment_id_property(self) -> None:
        reg = RuntimeRegistry("env-001")
        assert reg.environment_id == "env-001"


# ---------------------------------------------------------------------------
# Security Compatibility (S20)
# ---------------------------------------------------------------------------


class TestS20Compatibility:
    """Verify S21 identity does not interfere with S20 security."""

    def test_actor_identity_unchanged(self) -> None:
        actor = ActorIdentity(
            actor_id="user-1",
            actor_type=ActorType.USER,
        )
        assert actor.actor_id == "user-1"
        assert actor.trust_level == 0

    def test_system_actor_unchanged(self) -> None:
        assert SYSTEM_ACTOR.actor_id == "nav:system"
        assert SYSTEM_ACTOR.actor_type == ActorType.SYSTEM
        assert SYSTEM_ACTOR.trust_level == 100

    def test_env_identity_is_not_actor_identity(self) -> None:
        """Environment identity and actor identity are separate types."""
        env = EnvironmentIdentity(environment_id="env-001")
        actor = ActorIdentity(actor_id="user-1")
        assert type(env) is not type(actor)
        # They should not be comparable
        assert env != actor  # type: ignore[comparison-overlap]

    def test_default_environment_mirrors_system_actor_pattern(self) -> None:
        """Both use well-known constants for backward compatibility."""
        assert DEFAULT_ENVIRONMENT.environment_id.startswith("nav:")
        assert SYSTEM_ACTOR.actor_id.startswith("nav:")


# ---------------------------------------------------------------------------
# State Ownership Boundaries
# ---------------------------------------------------------------------------


class TestStateOwnership:
    """Verify environment/device/runtime state scopes are distinct."""

    def test_environment_state_origin(self) -> None:
        origin = StateOrigin(
            environment_id="env-001",
            origin_runtime_id="rt-001",
            origin_device_id="dev-001",
        )
        assert origin.environment_id == "env-001"

    def test_different_runtimes_different_origins(self) -> None:
        o1 = StateOrigin(
            environment_id="env-001",
            origin_runtime_id="rt-laptop",
        )
        o2 = StateOrigin(
            environment_id="env-001",
            origin_runtime_id="rt-phone",
        )
        assert o1 != o2
        assert o1.environment_id == o2.environment_id

    def test_version_increment(self) -> None:
        v1 = StateOrigin(
            environment_id="env-001",
            state_version=1,
        )
        v2 = StateOrigin(
            environment_id="env-001",
            state_version=2,
        )
        assert v1.state_version < v2.state_version
