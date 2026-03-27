import os
from pathlib import Path

from data import DATA_DIR


class ModelConfig:
    # LLM used by CrewAI agents
    MODEL = "ollama/phi3.5"

    # Temperature and sampling parameters
    TEMPERATURE = 0.2
    TOP_P = 0.7
    TOP_K = 20

    # Ollama connection (used when running a local model)
    OLLAMA_HOST = "http://localhost:11434"

    # Embedding model for CrewAI memory
    EMBEDDING_MODEL = "mxbai-embed-large"

    # This is taken from docker-compose environment variable
    EMBEDDER_URL = os.getenv("EMBEDDER_URL", "http://0.0.0.0:8009")
    EMBEDDER_TIMEOUT_SECONDS = float(os.getenv("EMBEDDER_TIMEOUT_SECONDS", "120"))
    EMBEDDER_BATCH_SIZE = int(os.getenv("EMBEDDER_BATCH_SIZE", "32"))


class DocumentConfig:
    BOOKS_DIR_PATH = Path(DATA_DIR) / "books"
    BOOKS_DIR_PATH.mkdir(parents=True, exist_ok=True)

    # Chunk size in characters
    CHUNK_SIZE = 1500
    CHUNK_OVERLAP = 150

    # Separators for recursive splitting (Swedish-aware)
    SEPARATORS = ["\n\n", "\n", ".", "!", "?"]


class VectorConfig:
    VECTORSTORE_DIR_PATH = Path(DATA_DIR) / "vectorstore"
    VECTORSTORE_DIR_PATH.mkdir(parents=True, exist_ok=True)

    COLLECTION_NAME_BOOKS = "books"

    # Retrieval parameters (number of chunks to retrieve for a query)
    RETRIEVAL_TOP_K = 20


class AppConfig:
    # API settings
    API_HOST = "0.0.0.0"
    API_PORT = 8100
    API_TITLE = "Cliston"
    API_VERSION = "0.1.0"

    # Logging
    LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
