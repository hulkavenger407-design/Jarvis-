"""
Capability Registry Subsystem (Compatibility Wrapper).

This module is a thin wrapper that re-exports the new `capability_registry` package
to maintain backward compatibility with obsolete imports.
"""

from .capability_registry.errors import (
    CapabilityDuplicateError,
    CapabilityNotFoundError,
    CapabilityRegistryError,
    CapabilityValidationError,
    ProviderNotFoundError,
)
from .capability_registry.interfaces import ICapability, ILifecycleCapability
from .capability_registry.models import (
    CapabilityDescriptor,
    CapabilityHandle,
    CapabilityMetadata,
    CapabilityState,
    CapabilityVersion,
)
from .capability_registry.registry import CapabilityRegistry, IProviderRegistry
from .capability_registry.shim import Capability

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
    "Capability",
]
