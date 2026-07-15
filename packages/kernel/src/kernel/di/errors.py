"""
Dependency Injection Exceptions
"""

class DependencyInjectionError(Exception):
    """Base exception for Dependency Injection operations."""
    pass


class ServiceNotFoundError(DependencyInjectionError):
    """Raised when a dependency cannot be resolved because it is not registered."""
    pass


class ResolutionError(DependencyInjectionError):
    """Raised when a dependency cannot be resolved due to lifecycle or structural issues."""
    pass


class CircularDependencyError(ResolutionError):
    """Raised when a circular dependency is detected during resolution."""
    pass
