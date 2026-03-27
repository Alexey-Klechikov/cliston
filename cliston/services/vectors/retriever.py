import logging
import re

from services.document.models import Chunk
from services.vectors.store import VectorStore


class HybridRetriever:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

        logging.info("HybridRetriever initialized")

    def _rerank_with_keywords(self, query: str, results: list[Chunk]) -> None:
        # Extract keywords from query (simple approach)
        keywords = set(re.findall(r"\b\w+\b", query.lower()))
        keywords = {kw for kw in keywords if len(kw) > 3}  # Filter short words

        # Calculate keyword score for each result
        for result in results:
            text_words = set(re.findall(r"\b\w+\b", result.text.lower()))
            keyword_overlap = len(keywords & text_words)
            result.keyword_score = keyword_overlap / max(len(keywords), 1)

        # Sort by combined score (vector distance + keyword score)
        # Lower distance is better, higher keyword score is better
        results.sort(key=lambda r: (r.distance, -r.keyword_score))

    async def retrieve(self, query: str, use_keyword: bool = True) -> list[Chunk]:
        vector_result_chunks = await self.vector_store.query(query)

        if use_keyword:
            self._rerank_with_keywords(query, vector_result_chunks)

        return vector_result_chunks

    def format_context(self, chunks: list[Chunk], include_metadata: bool = True) -> str:
        context_parts = []
        for i, chunk in enumerate(chunks):
            text = chunk.text
            if include_metadata:
                metadata = chunk.metadata
                source = metadata.source if metadata and metadata.source else "unknown"
                header = f"[Chunk {i + 1}/{len(chunks)} from {source}]"
                context_parts.append(f"{header}\n{text}")
            else:
                context_parts.append(text)

        return "\n\n---\n\n".join(context_parts)
