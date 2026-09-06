"""Runtime registry — S21.

In-memory registry of active runtimes within a NAV environment.
Tracks which runtimes are currently associated with the environment.
"""

from __future__ import annotations

from core.contracts.environment import (
    RuntimeDescriptor,
    RuntimeStatus,
)


class RuntimeRegistry:
    """In-memory registry of runtime instances.

    Tracks active runtimes within a NAV environment. Deliberately
    simple — no persistence, no networking. Establishes the concept
    of runtime membership within an environment.
    """

    def __init__(self, environment_id: str) -> None:
        self._environment_id = environment_id
        self._runtimes: dict[str, RuntimeDescriptor] = {}

    @property
    def environment_id(self) -> str:
        """The environment this registry belongs to."""
        return self._environment_id

    def register(self, descriptor: RuntimeDescriptor) -> None:
        """Register a runtime with the environment.

        Raises ValueError if the descriptor's environment_id does
        not match this registry's environment_id.
        """
        if descriptor.runtime.environment_id != self._environment_id:
            raise ValueError(
                f"Runtime environment_id "
                f"'{descriptor.runtime.environment_id}' does not match "
                f"registry environment_id '{self._environment_id}'"
            )
        self._runtimes[descriptor.runtime.runtime_id] = descriptor

    def unregister(self, runtime_id: str) -> None:
        """Remove a runtime from the registry."""
        self._runtimes.pop(runtime_id, None)

    def get(self, runtime_id: str) -> RuntimeDescriptor | None:
        """Look up a runtime by ID."""
        return self._runtimes.get(runtime_id)

    def active_runtimes(self) -> tuple[RuntimeDescriptor, ...]:
        """Return all runtimes with ACTIVE status."""
        return tuple(
            d
            for d in self._runtimes.values()
            if d.runtime.status == RuntimeStatus.ACTIVE
        )

    @property
    def count(self) -> int:
        """Total number of registered runtimes."""
        return len(self._runtimes)

    def clear(self) -> None:
        """Remove all registered runtimes."""
        self._runtimes.clear()
