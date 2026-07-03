"""
Config Package

Environment validation and configuration management.
"""

class ConfigManager:
    """Manages application configuration settings."""
    def __init__(self) -> None:
        self.settings: dict[str, str] = {}

    def get(self, key: str, default: str = "") -> str:
        return self.settings.get(key, default)
