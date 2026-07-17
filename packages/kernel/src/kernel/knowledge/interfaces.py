from typing import Any, Protocol


class IEmbeddingModel(Protocol):
    """
    Generates vector representations of text.
    """

    async def embed_text(self, text: str) -> list[float]:
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...


class IIndexingPipeline(Protocol):
    """
    Manages document ingestion, chunking, and embedding.
    """

    async def ingest_document(
        self, document_id: str, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        ...

    async def index_documents(self) -> None:
        ...
