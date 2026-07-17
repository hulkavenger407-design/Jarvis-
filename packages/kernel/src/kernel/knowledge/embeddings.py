from .errors import EmbeddingError
from .interfaces import IEmbeddingModel


class EmbeddingService:
    """Orchestrates embedding operations."""

    def __init__(self, embedding_model: IEmbeddingModel) -> None:
        self._model = embedding_model

    async def generate_embedding(self, text: str) -> list[float]:
        try:
            return await self._model.embed_text(text)
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embedding: {e}") from e

    async def generate_batch_embeddings(self, texts: list[str]) -> list[list[float]]:
        try:
            return await self._model.embed_batch(texts)
        except Exception as e:
            raise EmbeddingError(f"Failed to generate batch embeddings: {e}") from e
