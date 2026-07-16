"""
Capability Registry Subsystem Models.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class CapabilityState(StrEnum):
    """
    Represents the operational state of a capability.
    """

    REGISTERED = "REGISTERED"
    INITIALIZING = "INITIALIZING"
    HEALTHY = "HEALTHY"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    RETIRING = "RETIRING"
    TERMINATED = "TERMINATED"


@dataclass(frozen=True)
class CapabilityVersion:
    """
    Represents the version of a capability.
    """

    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class CapabilityMetadata:
    """
    Metadata associated with a capability.
    """

    description: str
    author: str = ""
    license: str = ""
    tags: list[str] = field(default_factory=list)
    custom_data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CapabilityDescriptor:
    """
    Describes a capability to be registered in the system.
    """

    id: str
    name: str
    version: CapabilityVersion
    provider_id: str
    interface: Any  # The protocol/interface this capability implements
    metadata: CapabilityMetadata
    permissions_required: list[str] = field(default_factory=list)


@dataclass
class CapabilityHandle:
    """
    Represents a registered capability handle in the registry.
    """

    descriptor: CapabilityDescriptor
    state: CapabilityState = CapabilityState.REGISTERED
    implementation: Any = None  # The concrete instance of the capability
