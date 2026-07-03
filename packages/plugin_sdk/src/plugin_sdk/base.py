"""
Plugin SDK

Base classes and tools for building capabilities and extensions.
"""

class Plugin:
    """Base class for all Chhaya plugins."""
    @property
    def name(self) -> str:
        raise NotImplementedError

    def initialize(self) -> None:
        """Called when the plugin is loaded by the kernel."""
        pass
