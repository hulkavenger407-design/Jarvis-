from typing import Any

from .errors import IndexingError
from .interfaces import IIndexingPipeline


class IndexingService:
    """Manages document ingestion and indexing via IIndexingPipeline."""

    def __init__(self, pipeline: IIndexingPipeline) -> None:
        self._pipeline = pipeline

    async def ingest_document(
        self, document_id: str, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        try:
            await self._pipeline.ingest_document(document_id, content, metadata)
        except Exception as e:
            raise IndexingError(f"Failed to ingest document {document_id}: {e}") from e

    async def process_index(self) -> None:
        try:
            await self._pipeline.index_documents()
        except Exception as e:
            raise IndexingError(f"Failed to process index: {e}") from e
