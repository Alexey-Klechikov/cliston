import hashlib
import logging

from pydantic import BaseModel
from services.document.models import Chunk, ChunkMetadata


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

    @staticmethod
    def get_chunk_hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

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
            content_hash = ChunksTracker.get_chunk_hash(text)

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
