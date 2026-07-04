"""
Configuration Manager Subsystem.

Provides environment validation, loading, and type-safe retrieval of
configuration values for the Chhaya Kernel.
"""
from collections.abc import Sequence
from typing import Any

from .provider import ConfigProvider, DictionaryProvider, EnvironmentProvider


class ConfigError(Exception):
    """Raised when a configuration value is missing or invalid."""
    pass


class ConfigManager:
    """
    Manages application configuration settings using a chain of ConfigProviders.
    Providers are queried in order; the first non-None value is returned.
    """

    def __init__(
        self,
        initial_config: dict[str, Any] | None = None,
        providers: Sequence[ConfigProvider] | None = None
    ) -> None:
        """
        Initializes the configuration manager.

        Args:
            providers: A sequence of configuration providers. Ordered by priority.
            initial_config: A legacy dictionary of overrides (prepended as a DictionaryProvider).
        """
        self._providers: list[ConfigProvider] = list(providers) if providers else []

        # Add default providers if not explicitly defined
        if initial_config:
            self._providers.insert(0, DictionaryProvider(initial_config))

        if not providers:
            self._providers.append(EnvironmentProvider())

    def add_provider(self, provider: ConfigProvider) -> None:
        """Adds a provider to the end of the fallback chain."""
        self._providers.append(provider)

    def insert_provider(self, provider: ConfigProvider, index: int = 0) -> None:
        """Inserts a provider at a specific priority level (0 = highest priority)."""
        self._providers.insert(index, provider)

    def get_str(self, key: str, default: str | None = None) -> str:
        """
        Retrieves a string configuration value.

        Args:
            key: The configuration key.
            default: The fallback value if not found.

        Returns:
            The configuration value as a string.

        Raises:
            ConfigError: If the key is not found and no default is provided.
        """
        val = self._get_raw(key, default)
        if val is None:
            raise ConfigError(f"Missing required configuration key: {key}")
        return str(val)

    def get_int(self, key: str, default: int | None = None) -> int:
        """
        Retrieves an integer configuration value.
        """
        val = self._get_raw(key, default)
        if val is None:
            raise ConfigError(f"Missing required configuration key: {key}")

        try:
            return int(val)
        except (ValueError, TypeError):
            raise ConfigError(f"Configuration key '{key}' must be an integer, got: {val}")

    def get_bool(self, key: str, default: bool | None = None) -> bool:
        """
        Retrieves a boolean configuration value.
        Recognizes 'true', '1', 'yes', 'on' as True.
        """
        val = self._get_raw(key, default)
        if val is None:
            raise ConfigError(f"Missing required configuration key: {key}")

        if isinstance(val, bool):
            return val

        truthy = {"true", "1", "yes", "on"}
        return str(val).lower() in truthy

    def _get_raw(self, key: str, default: Any = None) -> Any:
        """Internal helper to fetch from the provider chain sequentially."""
        for provider in self._providers:
            val = provider.get(key)
            if val is not None:
                return val
        return default
