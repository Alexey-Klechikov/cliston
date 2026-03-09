import hashlib
import logging
from typing import Any

import chromadb
import numpy as np
from config import VectorConfig
from pydantic import BaseModel
from services.documents.models import Chunk, ChunkMetadata
from services.vectors.embedder import EmbeddingService


def get_chunk_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class ChunksTracker(BaseModel):
    existing_chunks: dict[str, Chunk] = {}
    new_chunks: list[Chunk] = []
    skipped_chunks: int = 0

    seen_hashes: set[str] = set()
    new_texts: list[str] = []
    new_metadatas: list[ChunkMetadata] = []
    new_ids: list[str] = []
    duplicate_in_batch: int = 0

    @property
    def total_new_chunks(self) -> int:
        return len(self.new_chunks)

    def reset(self) -> None:
        self.new_chunks.clear()
        self.skipped_chunks = 0
        self.seen_hashes.clear()
        self.new_texts.clear()
        self.new_metadatas.clear()
        self.new_ids.clear()
        self.duplicate_in_batch = 0

    def add_existing_chunks(self, chunks: dict[str, Chunk]) -> None:
        self.existing_chunks = chunks
        self.seen_hashes = set(chunks.keys())

    def add_new_chunks(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            text = chunk.text.strip()
            content_hash = get_chunk_hash(text)

            if content_hash in self.existing_chunks:
                logging.debug(f"Skipping existing chunk (hash: {content_hash[:8]}...)")
                self.skipped_chunks += 1
                continue

            if content_hash in self.seen_hashes:
                logging.debug(f"Skipping duplicate chunk within batch (hash: {content_hash[:8]}...)")
                self.duplicate_in_batch += 1
                self.skipped_chunks += 1
                continue

            self.seen_hashes.add(content_hash)
            self.new_ids.append(f"chunk_{content_hash}")
            self.new_chunks.append(chunk)
            self.new_texts.append(text)
            self.new_metadatas.append(chunk.metadata)


class VectorStore:
    def __init__(
        self,
        tenant_id: str,
        collection_name: str = VectorConfig.COLLECTION_NAME,
        embedding_service: EmbeddingService | None = None,
    ):
        self.tenant_id = tenant_id
        self.collection_name = collection_name
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store_dir = VectorConfig.get_dir_path(tenant_id)

        # Initialize Chroma client with tenant-specific path
        self.client = chromadb.PersistentClient(
            path=str(self.vector_store_dir),
            settings=chromadb.Settings(allow_reset=True, anonymized_telemetry=False),  # type: ignore
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})

        # This is an object to track new and skipped chunks during the add_documents process
        self.chunks_tracker = ChunksTracker()

        logging.info("VectorStore initialized")

    def _get_existing_chunks_from_collection(self) -> dict[str, Chunk]:
        existing_chunks = {}
        try:
            all_data = self.collection.get(include=["documents", "metadatas"])
            if not (all_data and all_data["documents"]):
                logging.info("No existing chunks found in vector store")
                return existing_chunks

            for id, document_text, metadata in zip(
                all_data["ids"],
                all_data["documents"],
                all_data["metadatas"],  # type: ignore
            ):
                content_hash = get_chunk_hash(document_text)

                existing_chunks[content_hash] = Chunk(
                    id=id,
                    text=document_text,
                    metadata=ChunkMetadata.model_validate(metadata),
                )

            logging.info(f"Found {len(existing_chunks)} existing chunks in vector store")
            return existing_chunks

        except Exception as e:
            logging.error(f"Error getting existing chunks: {e}")
            return existing_chunks

    def _add_new_chunks_to_collection(self, embeddings: list[list[float]]) -> None:
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

    def add_documents(self, chunks: list[Chunk], skip_existing_chunks: bool = True) -> None:
        self.chunks_tracker.reset()

        if not chunks:
            logging.warning("No chunks provided to add_documents")
            return

        if skip_existing_chunks:
            existing_chunks = self._get_existing_chunks_from_collection()
            self.chunks_tracker.add_existing_chunks(chunks=existing_chunks)

        self.chunks_tracker.add_new_chunks(chunks=chunks)
        if not self.chunks_tracker.new_chunks:
            logging.info(f"All {self.chunks_tracker.skipped_chunks} chunks already exist in the vector store")
            return

        # Generate embeddings only for new chunks
        logging.info(
            f"Generating embeddings for {self.chunks_tracker.total_new_chunks} "
            f"new chunks (skipped {self.chunks_tracker.skipped_chunks} "
            f"existing/duplicates, {self.chunks_tracker.duplicate_in_batch} duplicate-in-batch)...",
        )
        embeddings = self.embedding_service.embed_texts(self.chunks_tracker.new_texts)

        # Verify embeddings were generated
        if len(embeddings) != len(self.chunks_tracker.new_texts):
            raise ValueError(
                "Embedding count mismatch: generated {} embeddings for {} texts".format(
                    len(embeddings),
                    len(self.chunks_tracker.new_texts),
                ),
            )

        self._add_new_chunks_to_collection(embeddings=embeddings)

    def query(self, query_text: str) -> list[Chunk]:
        retrieved_documents = []

        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query_text)

        # Query collection
        results = self.collection.query(query_embeddings=[query_embedding], n_results=VectorConfig.RETRIEVAL_TOP_K)

        if not (results and results["documents"] and len(results["documents"]) > 0):
            logging.info(f"No relevant chunks found for query: '{query_text}'")
            return retrieved_documents

        # Format results
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

    def clear(self) -> None:
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logging.info("Vector store cleared")
