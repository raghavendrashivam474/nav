from typing import Dict, List
from core.contracts.capability import Capability

class CapabilityRegistry:
    def __init__(self) -> None:
        self._capabilities: Dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        if capability.name in self._capabilities:
            raise ValueError(f"Capability '{capability.name}' is already registered.")
        self._capabilities[capability.name] = capability

    def get(self, name: str) -> Capability:
        if name not in self._capabilities:
            raise KeyError(f"Capability '{name}' is not registered.")
        return self._capabilities[name]

    def list_capabilities(self) -> List[str]:
        return list(self._capabilities.keys())
