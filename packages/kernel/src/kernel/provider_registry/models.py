"""
Provider Registry Models.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderMetadata:
    """Metadata describing a provider."""

    id: str
    name: str
    version: str
    description: str
    provided_capabilities: Sequence[str] = field(default_factory=list)
