import logging
from typing import Any

import httpx
from config import ModelConfig


class EmbeddingService:
    def __init__(self):
        self._embedder_url = ModelConfig.EMBEDDER_URL
        self._client: httpx.Client | None = None

        logging.info("EmbeddingService initialized")

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=30.0)
        return self._client

    def _embed_remote(self, texts: list[str]) -> list[list[float]]:
        if not self._embedder_url:
            raise RuntimeError("EMBEDDER_URL is not configured")

        payload = {"texts": texts}
        client = self._get_client()
        response = client.post(f"{self._embedder_url.rstrip('/')}/embed", json=payload)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list):
            raise RuntimeError("Embedder response missing embeddings")
        return embeddings

    def embed_text(self, text: str) -> list[float]:
        if not text:
            logging.warning("Empty text provided for embedding")
            return []

        return self._embed_remote([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            logging.warning("No texts provided to embed")
            return []

        logging.info(f"Embedding {len(texts)} texts via remote embedder")
        embeddings = self._embed_remote(texts)
        logging.info(f"Successfully embedded {len(embeddings)}/{len(texts)} texts")
        return embeddings
