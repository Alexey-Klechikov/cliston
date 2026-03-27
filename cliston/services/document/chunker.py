import logging

from config import DocumentConfig
from langchain_text_splitters import RecursiveCharacterTextSplitter
from services.document.models import Chunk, ChunkMetadata


class DocumentChunker:
    def __init__(self):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=DocumentConfig.CHUNK_SIZE,
            chunk_overlap=DocumentConfig.CHUNK_OVERLAP,
            separators=DocumentConfig.SEPARATORS,
            length_function=len,
        )
        logging.info("Initialized DocumentChunker")

    def chunk_with_metadata(self, text: str, source: str = "unknown") -> list[Chunk]:
        chunks = self.splitter.split_text(text)
        logging.info(f"Chunked text into {len(chunks)} chunks")
        return [
            Chunk(text=chunk, metadata=ChunkMetadata(source=source, chunk_index=i)) for i, chunk in enumerate(chunks)
        ]
