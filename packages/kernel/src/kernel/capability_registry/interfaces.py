"""
Capability Registry Subsystem Interfaces.
"""

from typing import Protocol, runtime_checkable

from .models import CapabilityDescriptor


@runtime_checkable
class ICapability(Protocol):
    """
    Base protocol that all concrete capabilities must implement.
    """

    @property
    def descriptor(self) -> CapabilityDescriptor:
        """Return the descriptor for this capability."""
        ...


@runtime_checkable
class ILifecycleCapability(Protocol):
    """
    Optional protocol for capabilities that require lifecycle hooks.
    """

    async def initialize(self) -> None:
        """Called immediately after successful registration."""
        ...

    async def shutdown(self) -> None:
        """Called immediately before successful unregistration."""
        ...
