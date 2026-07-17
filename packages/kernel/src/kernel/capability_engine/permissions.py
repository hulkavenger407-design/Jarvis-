from enum import Enum
from typing import Protocol

from kernel.capability_engine.models import CapabilityContext


class CapabilityPermission(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class CapabilityAuthorizer(Protocol):
    """Protocol for validating permissions."""

    async def authorize(self, context: CapabilityContext) -> bool: ...
