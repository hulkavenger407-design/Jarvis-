from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentChunk:
    """A chunk of a document."""
    chunk_id: str
    document_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievedContext:
    """The assembled context for a given query."""
    query: str
    chunks: list[DocumentChunk]
    metadata: dict[str, Any] = field(default_factory=dict)
