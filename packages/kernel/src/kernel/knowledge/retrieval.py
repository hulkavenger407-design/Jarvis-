from typing import Any

from kernel.memory.interfaces import IVectorStore

from .embeddings import EmbeddingService
from .errors import RetrievalError
from .models import DocumentChunk


class RetrievalService:
    """Handles vector lookup and semantic retrieval."""

    def __init__(self, vector_store: IVectorStore, embedding_service: EmbeddingService) -> None:
        self._vector_store = vector_store
        self._embedding_service = embedding_service

    async def retrieve(
        self, query: str, limit: int = 10, metadata_filter: dict[str, Any] | None = None
    ) -> list[DocumentChunk]:
        """Retrieves chunks by converting query to vector and searching store."""
        try:
            # We assume embedding is used by the underlying vector store implementation
            # or we generate it here if needed. For now, we delegate to search.
            # In a real implementation we might pass the vector itself if IVectorStore
            # accepts vectors. Since IVectorStore takes 'query: Any', we can pass the
            # text query or a dict with vector.
            query_vector = await self._embedding_service.generate_embedding(query)
            search_query: dict[str, Any] = {"text": query, "vector": query_vector}

            if metadata_filter:
                search_query["filter"] = metadata_filter

            results = await self._vector_store.search(search_query, limit=limit)

            chunks = []
            for result in results:
                record = result.record
                # Convert memory record back to document chunk
                chunk = DocumentChunk(
                    chunk_id=record.key,
                    document_id=record.metadata.get("document_id", ""),
                    content=str(record.value),
                    metadata=record.metadata,
                )
                chunks.append(chunk)

            return chunks

        except Exception as e:
            raise RetrievalError(f"Failed to retrieve documents for query '{query}': {e}") from e
