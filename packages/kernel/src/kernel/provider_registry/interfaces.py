"""
Provider Registry Interfaces.
"""

from typing import Protocol, runtime_checkable

from .models import ProviderMetadata


@runtime_checkable
class IProvider(Protocol):
    """
    Base protocol that all concrete providers must implement.
    The exact interface can vary, but this ensures a common denominator.
    """

    @property
    def metadata(self) -> ProviderMetadata:
        """Return the metadata for this provider."""
        ...


@runtime_checkable
class ILifecycleProvider(Protocol):
    """
    Optional protocol for providers that require lifecycle hooks.
    """

    async def initialize(self) -> None:
        """Called immediately after successful registration."""
        ...

    async def shutdown(self) -> None:
        """Called immediately before successful unregistration."""
        ...
