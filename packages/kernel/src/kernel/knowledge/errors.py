class KnowledgeError(Exception):
    """Base exception for the Knowledge Layer."""


class EmbeddingError(KnowledgeError):
    """Exception raised for errors during embedding generation."""


class IndexingError(KnowledgeError):
    """Exception raised for errors during indexing."""


class RetrievalError(KnowledgeError):
    """Exception raised for errors during retrieval."""
