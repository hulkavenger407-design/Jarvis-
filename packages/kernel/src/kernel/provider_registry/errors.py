"""
Provider Registry Errors.
"""


class ProviderRegistryError(Exception):
    """Base exception for all Provider Registry errors."""
    pass


class ProviderDuplicateError(ProviderRegistryError):
    """Raised when attempting to register a provider ID that already exists."""
    pass


class ProviderValidationError(ProviderRegistryError):
    """Raised when a provider or its metadata fails validation."""
    pass


class ProviderNotFoundError(ProviderRegistryError):
    """Raised when a requested provider cannot be found."""
    pass
