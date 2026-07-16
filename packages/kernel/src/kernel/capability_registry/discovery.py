"""
Capability Registry Subsystem Discovery.
"""


from .interfaces import ICapability


class StaticCapabilityDiscovery:
    """
    A simple in-memory/static capability discovery abstraction.
    Does not perform hot-loading or filesystem scanning.
    """

    def __init__(self) -> None:
        self._capabilities: list[ICapability] = []

    def add_capability(self, capability: ICapability) -> None:
        """
        Statically add a capability to be discovered later.
        """
        self._capabilities.append(capability)

    def discover_capabilities(self) -> list[ICapability]:
        """
        Return all statically added capabilities.
        """
        return list(self._capabilities)
