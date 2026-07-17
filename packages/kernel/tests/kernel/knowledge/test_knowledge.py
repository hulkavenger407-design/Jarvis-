from typing import Any

import pytest
from kernel.knowledge.context_builder import ContextBuilder
from kernel.knowledge.embeddings import EmbeddingService
from kernel.knowledge.errors import EmbeddingError, IndexingError, RetrievalError
from kernel.knowledge.indexing import IndexingService
from kernel.knowledge.interfaces import IEmbeddingModel, IIndexingPipeline
from kernel.knowledge.knowledge_engine import KnowledgeEngine
from kernel.knowledge.retrieval import RetrievalService
from kernel.memory.interfaces import IVectorStore
from kernel.memory.models import MemoryRecord, MemorySearchResult, MemoryTier


class MockEmbeddingModel(IEmbeddingModel):
    async def embed_text(self, text: str) -> list[float]:
        if text == "fail":
            raise ValueError("Intentional failure")
        return [0.1, 0.2, 0.3]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if "fail" in texts:
            raise ValueError("Intentional batch failure")
        return [[0.1, 0.2, 0.3] for _ in texts]


class MockIndexingPipeline(IIndexingPipeline):
    def __init__(self) -> None:
        self.ingested: list[tuple[str, str, dict[str, Any] | None]] = []
        self.indexed = False
        self.fail_index = False

    async def ingest_document(
        self, document_id: str, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        if document_id == "fail":
            raise ValueError("Intentional ingestion failure")
        self.ingested.append((document_id, content, metadata))

    async def index_documents(self) -> None:
        if self.fail_index:
            raise ValueError("Intentional indexing failure")
        self.indexed = True


class MockVectorStore(IVectorStore):
    async def search(self, query: Any, limit: int = 10) -> list[MemorySearchResult]:
        if isinstance(query, dict) and query.get("text") == "fail":
            raise ValueError("Intentional retrieval failure")
        return [
            MemorySearchResult(
                record=MemoryRecord(
                    tier=MemoryTier.WORKING,
                    namespace="test",
                    key="chunk-1",
                    value="content of chunk 1",
                    metadata={"document_id": "doc-1"},
                ),
                score=0.9,
            )
        ]

    async def insert(self, record: MemoryRecord) -> None:
        pass

    async def delete(self, key: str) -> None:
        pass

    async def clear(self) -> None:
        pass


@pytest.mark.asyncio
async def test_embedding_service() -> None:
    model = MockEmbeddingModel()
    service = EmbeddingService(model)

    res = await service.generate_embedding("hello")
    assert res == [0.1, 0.2, 0.3]

    batch_res = await service.generate_batch_embeddings(["hello", "world"])
    assert batch_res == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]

    with pytest.raises(EmbeddingError):
        await service.generate_embedding("fail")

    with pytest.raises(EmbeddingError):
        await service.generate_batch_embeddings(["fail"])


@pytest.mark.asyncio
async def test_indexing_service() -> None:
    pipeline = MockIndexingPipeline()
    service = IndexingService(pipeline)

    await service.ingest_document("doc-1", "content")
    assert pipeline.ingested == [("doc-1", "content", None)]

    await service.process_index()
    assert pipeline.indexed is True

    with pytest.raises(IndexingError):
        await service.ingest_document("fail", "content")

    pipeline.fail_index = True
    with pytest.raises(IndexingError):
        await service.process_index()


@pytest.mark.asyncio
async def test_retrieval_service() -> None:
    vector_store = MockVectorStore()
    embedding_service = EmbeddingService(MockEmbeddingModel())
    service = RetrievalService(vector_store, embedding_service)

    chunks = await service.retrieve("query")
    assert len(chunks) == 1
    assert chunks[0].chunk_id == "chunk-1"
    assert chunks[0].document_id == "doc-1"
    assert chunks[0].content == "content of chunk 1"

    chunks_with_filter = await service.retrieve("query", metadata_filter={"k": "v"})
    assert len(chunks_with_filter) == 1

    with pytest.raises(RetrievalError):
        await service.retrieve("fail")


@pytest.mark.asyncio
async def test_knowledge_engine() -> None:
    vector_store = MockVectorStore()
    embedding_service = EmbeddingService(MockEmbeddingModel())
    retrieval_service = RetrievalService(vector_store, embedding_service)
    indexing_service = IndexingService(MockIndexingPipeline())
    context_builder = ContextBuilder()

    engine = KnowledgeEngine(
        retrieval_service=retrieval_service,
        indexing_service=indexing_service,
        embedding_service=embedding_service,
        context_builder=context_builder,
    )

    context = await engine.retrieve_context("query")
    assert context.query == "query"
    assert len(context.chunks) == 1
    assert context.metadata["total_chunks"] == 1

    await engine.ingest_document("doc-1", "content")
    await engine.index_documents()

    mock_pipeline = indexing_service._pipeline
    assert getattr(mock_pipeline, "indexed") is True

    embeds = await engine.generate_embedding("query")
    assert embeds == [0.1, 0.2, 0.3]

    batch = await engine.generate_batch_embeddings(["query"])
    assert batch == [[0.1, 0.2, 0.3]]
