"""
Configuration Provider Protocol.

Defines the interface for all configuration sources (Env, YAML, JSON, API, etc).
"""
from typing import Any, Protocol


class ConfigProvider(Protocol):
    """
    Interface for providing configuration values.
    """
    def get(self, key: str) -> Any | None:
        """
        Retrieves a configuration value if it exists in this provider.

        Args:
            key: The configuration key to look up.

        Returns:
            The value if found, otherwise None.
        """
        ...
