import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import Field
from services.document.models import Chunk, ChunkMetadata

from cliston.settings import settings

SEPARATORS: list[str] = Field(default_factory=lambda: ["\n\n\n", "\n\n", "\n", ".", "!", "?"])


class DocumentChunker:
    def __init__(self):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=SEPARATORS,
            length_function=len,
        )
        logging.info("Initialized DocumentChunker")

    def chunk_with_metadata(self, text: str, source: str = "unknown") -> list[Chunk]:
        chunks = self.splitter.split_text(text)
        logging.info(f"Chunked text into {len(chunks)} chunks")
        return [
            Chunk(text=chunk, metadata=ChunkMetadata(source=source, chunk_index=i)) for i, chunk in enumerate(chunks)
        ]
