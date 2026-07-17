from .models import DocumentChunk, RetrievedContext


class ContextBuilder:
    """Assembles retrieved context for downstream consumers."""

    def build_context(self, query: str, chunks: list[DocumentChunk]) -> RetrievedContext:
        """Builds a context payload from retrieved chunks."""
        # Future enhancements can apply token budgets or ranking here.
        return RetrievedContext(
            query=query,
            chunks=chunks,
            metadata={"total_chunks": len(chunks)},
        )
