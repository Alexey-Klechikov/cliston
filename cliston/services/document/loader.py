import logging
from pathlib import Path

from config import DocumentConfig
from services.document.chunker import DocumentChunker
from services.document.models import Chunk, Document
from services.document.parser import SUPPORTED_EXTENSIONS, ParserFactory
from utils import asyncify


class DocumentLoader:
    def __init__(self, chunker: DocumentChunker | None = None):
        self.resources_dir = DocumentConfig.BOOKS_DIR_PATH
        self.chunker = chunker or DocumentChunker()
        logging.info("Initialized DocumentLoader")

    def _discover_documents(self) -> list[Path]:
        docs = []
        for extention in SUPPORTED_EXTENSIONS:
            docs.extend(self.resources_dir.glob(f"*{extention}"))

        logging.info(f"Discovered {len(docs)} documents")
        return sorted(docs)

    def _load_document(self, file_path: Path) -> Document:
        logging.info(f"Loading document: {file_path.name}")
        raw_text = ParserFactory.parse(file_path)
        chunks = self.chunker.chunk_with_metadata(raw_text, source=file_path.name)
        return Document(
            name=file_path.name,
            file_path=str(file_path),
            raw_text=raw_text,
            chunks=[Chunk.model_validate(i) for i in chunks],
        )

    @asyncify
    def get_all_chunks(self) -> list[Chunk]:
        all_chunks = []
        docs = self._discover_documents()

        for doc_path in docs:
            try:
                document = self._load_document(doc_path)
                all_chunks.extend(document.chunks)
            except Exception as e:
                logging.error(f"Failed to chunk {doc_path}: {e}")
                continue

        logging.info(f"Total chunks created: {len(all_chunks)}")
        return all_chunks
