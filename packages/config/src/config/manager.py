"""
Configuration Manager Subsystem.

Provides environment validation, loading, and type-safe retrieval of
configuration values for the Chhaya Kernel.
"""
import os
from typing import Any


class ConfigError(Exception):
    """Raised when a configuration value is missing or invalid."""
    pass


class ConfigManager:
    """
    Manages application configuration settings, falling back to environment variables.
    """

    def __init__(self, initial_config: dict[str, Any] | None = None) -> None:
        """
        Initializes the configuration manager.

        Args:
            initial_config: A dictionary of explicit overrides.
        """
        self._config: dict[str, Any] = initial_config or {}

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
        """Internal helper to fetch from explicit config first, then os.environ."""
        if key in self._config:
            return self._config[key]

        if key in os.environ:
            return os.environ[key]

        return default
