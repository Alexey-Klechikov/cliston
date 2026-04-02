import logging
from itertools import islice
from typing import Any

import httpx
import numpy as np

from cliston.settings import settings


class EmbeddingService:
    def __init__(self):
        self._embedder_url = settings.EMBEDDER_URL
        self._timeout_seconds = settings.EMBEDDER_TIMEOUT_SECONDS
        self._batch_size = max(1, settings.EMBEDDER_BATCH_SIZE)
        self._client: httpx.Client | None = None

        logging.info("EmbeddingService initialized")

    def _get_client(self) -> httpx.Client:
        """Returns a thread-local sync client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=httpx.Timeout(connect=10.0, read=self._timeout_seconds, write=30.0, pool=10.0),
            )
        return self._client

    def _iter_batches(self, texts: list[str]):
        iterator = iter(texts)
        while batch := list(islice(iterator, self._batch_size)):
            yield batch

    def _embed_remote(self, texts: list[str]) -> list[list[float]]:
        """Synchronous remote call."""
        if not self._embedder_url:
            raise RuntimeError("EMBEDDER_URL is not configured")

        payload = {"texts": texts}
        client = self._get_client()

        # Plain synchronous post
        response = client.post(f"{self._embedder_url.rstrip('/')}/embed", json=payload)
        response.raise_for_status()

        data: dict[str, Any] = response.json()
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list):
            raise RuntimeError("Embedder response missing embeddings")
        return embeddings

    def embed_text(self, text: str) -> np.ndarray:
        """Synchronous single text embedding."""
        if not text:
            logging.warning("Empty text provided for embedding")
            return np.array([], dtype=np.float32)

        raw = self._embed_remote([text])[0]
        return np.array(raw, dtype=np.float32)

    def embed_texts(self, texts: list[str]) -> list[np.ndarray]:
        """Synchronous batch embedding."""
        if not texts:
            logging.warning("No texts provided to embed")
            return []

        logging.info(
            "Embedding %s texts via sync remote embedder (batch_size=%s)",
            len(texts),
            self._batch_size,
        )

        embeddings: list[list[float]] = []
        total_batches = (len(texts) + self._batch_size - 1) // self._batch_size

        for batch_index, batch in enumerate(self._iter_batches(texts), start=1):
            logging.info(
                "Batch %s/%s (%s texts)",
                batch_index,
                total_batches,
                len(batch),
            )
            embeddings.extend(self._embed_remote(batch))

        return [np.array(e, dtype=np.float32) for e in embeddings]

    def close(self) -> None:
        """Close the sync client."""
        if self._client is not None:
            self._client.close()
            self._client = None


_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
