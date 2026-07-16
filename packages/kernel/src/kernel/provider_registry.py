"""
Provider Registry Subsystem (Compatibility Wrapper).

This module is a thin wrapper that re-exports the ProviderRegistry implementation
from the new `provider_registry` package to maintain backward compatibility.
"""

from .provider_registry.errors import ProviderRegistryError
from .provider_registry.models import ProviderMetadata
from .provider_registry.registry import ProviderRegistry

__all__ = [
    "ProviderRegistry",
    "ProviderMetadata",
    "ProviderRegistryError",
]
