from dataclasses import dataclass, field
from typing import Any

from .models import CapabilityDescriptor, CapabilityVersion, CapabilityMetadata

@dataclass(frozen=True)
class Capability:
    """
    Legacy Capability dataclass provided for backward compatibility.
    It acts as a shim that satisfies the new ICapability protocol.
    """
    name: str
    version: str
    description: str = ""
    provider_name: str = "core"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def descriptor(self) -> CapabilityDescriptor:
        version_str = self.version.split(".")
        major, minor, patch = 1, 0, 0
        if len(version_str) >= 3:
            try:
                major, minor, patch = int(version_str[0]), int(version_str[1]), int(version_str[2])
            except ValueError:
                pass

        return CapabilityDescriptor(
            id=f"{self.provider_name}.{self.name}",
            name=self.name,
            version=CapabilityVersion(major, minor, patch),
            provider_id=self.provider_name,
            interface=type("DummyShimInterface", (), {}),
            metadata=CapabilityMetadata(
                description=self.description,
                custom_data=self.metadata
            )
        )
