"""
Configuration Provider Protocol.

Defines the interface for all configuration sources (Env, YAML, JSON, API, etc).
"""
import os
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


class EnvironmentProvider:
    """Reads configuration from os.environ."""
    def get(self, key: str) -> Any | None:
        return os.environ.get(key)


class DictionaryProvider:
    """Reads configuration from a static dictionary."""
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data

    def get(self, key: str) -> Any | None:
        return self.data.get(key)
