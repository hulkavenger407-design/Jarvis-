"""
Provider Discovery Abstraction.
"""

from typing import Protocol, runtime_checkable

from .models import ProviderMetadata


@runtime_checkable
class IProviderDiscovery(Protocol):
    """
    Abstract interface for discovering providers.
    """

    async def discover_providers(self) -> list[ProviderMetadata]:
        """
        Discover and return a list of provider descriptors/metadata.
        """
        ...


class StaticProviderDiscovery:
    """
    Static/in-memory provider discovery implementation.
    Returns a predefined list of provider metadata.
    """

    def __init__(self, providers: list[ProviderMetadata] | None = None) -> None:
        """
        Initialize with an optional list of predefined provider metadata.
        """
        self._providers = providers or []

    async def discover_providers(self) -> list[ProviderMetadata]:
        """
        Return the pre-configured static list of providers.
        """
        return list(self._providers)
