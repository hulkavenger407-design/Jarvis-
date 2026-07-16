"""
Capability Registry Subsystem Errors.
"""

class CapabilityRegistryError(Exception):
    """Base exception for all Capability Registry errors."""
    pass


class CapabilityDuplicateError(CapabilityRegistryError):
    """Raised when attempting to register a capability that is already registered."""
    pass


class CapabilityValidationError(CapabilityRegistryError):
    """Raised when a capability fails validation checks."""
    pass


class ProviderNotFoundError(CapabilityRegistryError):
    """Raised when the associated provider for a capability cannot be found."""
    pass


class CapabilityNotFoundError(CapabilityRegistryError):
    """Raised when a requested capability is not found."""
    pass
