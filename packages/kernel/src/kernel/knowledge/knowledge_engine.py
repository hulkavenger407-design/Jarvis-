from typing import Any

from .context_builder import ContextBuilder
from .embeddings import EmbeddingService
from .indexing import IndexingService
from .models import RetrievedContext
from .retrieval import RetrievalService


class KnowledgeEngine:
    """Main orchestrator for the Knowledge Layer."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        indexing_service: IndexingService,
        embedding_service: EmbeddingService,
        context_builder: ContextBuilder,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._indexing_service = indexing_service
        self._embedding_service = embedding_service
        self._context_builder = context_builder

    async def retrieve_context(
        self, query: str, limit: int = 10, metadata_filter: dict[str, Any] | None = None
    ) -> RetrievedContext:
        """Retrieves and assembles context for a given query."""
        chunks = await self._retrieval_service.retrieve(query, limit, metadata_filter)
        return self._context_builder.build_context(query, chunks)

    async def ingest_document(
        self, document_id: str, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """Ingests a document through the indexing pipeline."""
        await self._indexing_service.ingest_document(document_id, content, metadata)

    async def index_documents(self) -> None:
        """Processes the indexing workflow."""
        await self._indexing_service.process_index()

    async def generate_embedding(self, text: str) -> list[float]:
        """Generates an embedding for the given text."""
        return await self._embedding_service.generate_embedding(text)

    async def generate_batch_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generates embeddings for a batch of texts."""
        return await self._embedding_service.generate_batch_embeddings(texts)
