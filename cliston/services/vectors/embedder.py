import asyncio
import logging
from itertools import islice
from typing import Any

import httpx
from config import ModelConfig


class EmbeddingService:
    def __init__(self):
        self._embedder_url = ModelConfig.EMBEDDER_URL
        self._timeout_seconds = ModelConfig.EMBEDDER_TIMEOUT_SECONDS
        self._batch_size = max(1, ModelConfig.EMBEDDER_BATCH_SIZE)
        self._client: httpx.AsyncClient | None = None

        logging.info("EmbeddingService initialized")

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10.0, read=self._timeout_seconds, write=30.0, pool=10.0),
            )
        return self._client

    def _iter_batches(self, texts: list[str]):
        iterator = iter(texts)
        while batch := list(islice(iterator, self._batch_size)):
            yield batch

    async def _embed_remote(self, texts: list[str]) -> list[list[float]]:
        if not self._embedder_url:
            raise RuntimeError("EMBEDDER_URL is not configured")

        payload = {"texts": texts}
        client = self._get_client()
        response = await client.post(f"{self._embedder_url.rstrip('/')}/embed", json=payload)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list):
            raise RuntimeError("Embedder response missing embeddings")
        return embeddings

    async def embed_text(self, text: str) -> list[float]:
        if not text:
            logging.warning("Empty text provided for embedding")
            return []

        return (await self._embed_remote([text]))[0]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            logging.warning("No texts provided to embed")
            return []

        logging.info(
            "Embedding %s texts via remote embedder (batch_size=%s, timeout=%ss)",
            len(texts),
            self._batch_size,
            self._timeout_seconds,
        )

        embeddings: list[list[float]] = []
        total_batches = (len(texts) + self._batch_size - 1) // self._batch_size

        for batch_index, batch in enumerate(self._iter_batches(texts), start=1):
            logging.info(
                "Embedding batch %s/%s via remote embedder (%s texts)",
                batch_index,
                total_batches,
                len(batch),
            )
            embeddings.extend(await self._embed_remote(batch))

        logging.info(f"Successfully embedded {len(embeddings)}/{len(texts)} texts")
        return embeddings

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def close(self) -> None:
        if self._client is None:
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.aclose())
            return

        loop.create_task(self.aclose())
