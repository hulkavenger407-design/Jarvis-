"""
Capability Registry Subsystem.
"""

from .discovery import StaticCapabilityDiscovery
from .errors import (
    CapabilityDuplicateError,
    CapabilityNotFoundError,
    CapabilityRegistryError,
    CapabilityValidationError,
    ProviderNotFoundError,
)
from .interfaces import ICapability, ILifecycleCapability
from .models import (
    CapabilityDescriptor,
    CapabilityHandle,
    CapabilityMetadata,
    CapabilityState,
    CapabilityVersion,
)
from .registry import CapabilityRegistry, IProviderRegistry

__all__ = [
    "CapabilityRegistry",
    "IProviderRegistry",
    "ICapability",
    "ILifecycleCapability",
    "CapabilityDescriptor",
    "CapabilityHandle",
    "CapabilityMetadata",
    "CapabilityState",
    "CapabilityVersion",
    "CapabilityDuplicateError",
    "CapabilityNotFoundError",
    "CapabilityRegistryError",
    "CapabilityValidationError",
    "ProviderNotFoundError",
    "StaticCapabilityDiscovery",
]
