"""
Dependency Injection Lifetimes
"""

import enum


class Lifetime(enum.Enum):
    """Defines the lifetime of a registered dependency."""

    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"
