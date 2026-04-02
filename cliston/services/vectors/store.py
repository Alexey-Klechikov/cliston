import asyncio
import logging
from collections.abc import Sequence
from typing import Any

import chromadb
import numpy as np
from data import VECTORSTORE_DIR_PATH
from services.document.models import Chunk, ChunkMetadata
from services.embedder.client import EmbeddingService
from services.vectors.models import ChunksTracker
from utils import asyncify

from cliston.settings import settings


class VectorStore:
    def __init__(
        self,
        collection_name: str = settings.COLLECTION_NAME_BOOKS,
        embedding_service: EmbeddingService | None = None,
    ):
        self.collection_name = collection_name
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store_dir = VECTORSTORE_DIR_PATH

        # Initialize Chroma client
        self.client = chromadb.PersistentClient(
            path=str(self.vector_store_dir),
            settings=chromadb.Settings(allow_reset=True, anonymized_telemetry=False),  # type: ignore
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})

        # This is an object to track new and skipped chunks during the add_documents process
        self.chunks_tracker = ChunksTracker()

        logging.info("VectorStore initialized")

    @asyncify
    def _get_existing_chunks_from_collection(self) -> dict[str, Chunk]:
        existing_chunks = {}
        try:
            all_data = self.collection.get(include=["documents", "metadatas"])
            if not (all_data and all_data["documents"]):
                logging.info("No existing chunks found in vector store")
                return existing_chunks

            for chunk_id, document_text, metadata in zip(
                all_data["ids"],
                all_data["documents"],
                all_data["metadatas"],  # type: ignore
            ):
                content_hash = ChunksTracker.get_chunk_hash(document_text)

                existing_chunks[content_hash] = Chunk(
                    id=chunk_id,
                    text=document_text,
                    metadata=ChunkMetadata.model_validate(metadata),
                )

            logging.info(f"Found {len(existing_chunks)} existing chunks in vector store")
            return existing_chunks

        except Exception as e:
            logging.error(f"Error getting existing chunks: {e}")
            return existing_chunks

    @asyncify
    def _add_new_chunks_to_collection(self, embeddings: Sequence[np.ndarray]) -> None:
        try:
            self.collection.add(
                ids=self.chunks_tracker.new_ids,
                embeddings=np.array(embeddings),
                documents=self.chunks_tracker.new_texts,
                metadatas=[i.model_dump(mode="json") for i in self.chunks_tracker.new_metadatas],
            )

            # Verify what was actually stored
            stored_count = self.collection.count()
            logging.info(
                f"Added {self.chunks_tracker.total_new_chunks} new chunks to vector store "
                f"(skipped {self.chunks_tracker.skipped_chunks} existing/duplicates, "
                f"{self.chunks_tracker.duplicate_in_batch} duplicate-in-batch) "
                f"| Total in store: {stored_count} chunks",
            )

            # Log first 3 chunks as verification
            for i, (chunk_id, text) in enumerate(
                zip(self.chunks_tracker.new_ids[:3], self.chunks_tracker.new_texts[:3]),
            ):
                preview = text[:80].replace("\n", " ")
                logging.debug(f"Stored chunk {i + 1}: {chunk_id[:16]}... → '{preview}'...")

        except Exception as e:
            logging.error(f"Error adding documents to vector store: {e}")
            raise

    def get_collection_info(self) -> dict[str, Any]:
        return {"name": self.collection.name, "count": self.collection.count(), "metadata": self.collection.metadata}

    async def add_documents(self, chunks: list[Chunk], skip_existing_chunks: bool = True) -> None:
        self.chunks_tracker.reset()

        if not chunks:
            logging.warning("No chunks provided to add_documents")
            return

        if skip_existing_chunks:
            existing_chunks = await self._get_existing_chunks_from_collection()
            self.chunks_tracker.add_existing_chunks(chunks=existing_chunks)

        self.chunks_tracker.add_new_chunks(chunks=chunks)
        if not self.chunks_tracker.new_chunks:
            logging.info(f"All {self.chunks_tracker.skipped_chunks} chunks already exist in the vector store")
            return

        logging.info(
            f"Generating embeddings for {self.chunks_tracker.total_new_chunks} "
            f"new chunks (skipped {self.chunks_tracker.skipped_chunks} "
            f"existing/duplicates, {self.chunks_tracker.duplicate_in_batch} duplicate-in-batch)...",
        )
        embeddings = self.embedding_service.embed_texts(self.chunks_tracker.new_texts)

        if len(embeddings) != len(self.chunks_tracker.new_texts):
            raise ValueError(
                "Embedding count mismatch: generated {} embeddings for {} texts".format(
                    len(embeddings),
                    len(self.chunks_tracker.new_texts),
                ),
            )

        await self._add_new_chunks_to_collection(embeddings=embeddings)

    async def query(self, query_text: str, top_k: int = settings.RETRIEVAL_TOP_K) -> list[Chunk]:
        retrieved_documents = []

        query_embedding = self.embedding_service.embed_text(query_text)
        results = await asyncio.to_thread(
            self.collection.query,
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        if not (results and results["documents"] and len(results["documents"]) > 0):
            logging.info(f"No relevant chunks found for query: '{query_text}'")
            return retrieved_documents

        for i, document in enumerate(results["documents"][0]):
            retrieved_documents.append(
                Chunk(
                    text=document,
                    metadata=ChunkMetadata.model_validate(results["metadatas"][0][i]),  # type: ignore
                    distance=results["distances"][0][i] if results["distances"] else 0.0,
                ),
            )

        logging.info(f"Query retrieved {len(retrieved_documents)} chunks")
        return retrieved_documents

    @asyncify
    def verify_storage(self) -> dict[str, Any]:
        all_data = self.collection.get(include=["documents", "metadatas", "embeddings"])
        total_count = len(all_data["ids"]) if all_data and all_data["ids"] else 0

        if total_count == 0:
            logging.warning("Vector store is empty - no chunks stored yet")
            return {
                "status": "empty",
                "total_chunks": 0,
                "chunks_with_text": 0,
                "chunks_with_embeddings": 0,
                "verified": False,
            }

        # Check for text content and embeddings
        chunks_with_text = 0
        chunks_with_embeddings = 0
        chunks_verified = []

        for i, chunk_id in enumerate(all_data["ids"]):
            has_text = bool(all_data["documents"][i]) if all_data["documents"] else False
            has_embedding = all_data["embeddings"] is not None and i < len(all_data["embeddings"])

            chunks_with_text += 1 if has_text else 0
            chunks_with_embeddings += 1 if has_embedding else 0

            # Collect sample for verification
            if i < 5:
                text_preview = (
                    all_data["documents"][i][:60].replace("\n", " ")
                    if has_text and all_data["documents"]
                    else "[NO TEXT]"
                )
                chunks_verified.append(
                    {
                        "id": chunk_id[:16],
                        "text_preview": text_preview,
                        "has_text": has_text,
                        "has_embedding": has_embedding,
                        "metadata": all_data["metadatas"][i] if all_data["metadatas"] else {},
                    },
                )

        # Generate report
        all_verified = (chunks_with_text == total_count) and (chunks_with_embeddings == total_count)

        report = {
            "status": "✓ VERIFIED" if all_verified else "⚠ INCOMPLETE",
            "total_chunks": total_count,
            "chunks_with_text": chunks_with_text,
            "chunks_with_embeddings": chunks_with_embeddings,
            "verified": all_verified,
            "sample_chunks": chunks_verified[:5],
            "message": (
                f"All {total_count} chunks have content and embeddings"
                if all_verified
                else f"WARNING: Missing text in {total_count - chunks_with_text} chunks or "
                f"embeddings in {total_count - chunks_with_embeddings} chunks"
            ),
        }

        return report

    @asyncify
    def clear(self) -> None:
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logging.info("Vector store cleared")


_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
