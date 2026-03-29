import os
from pathlib import Path

from data import DATA_DIR

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class ModelConfig:
    SUPERIOR_GEMINI_MODEL = "gemini-2.5-flash"
    ACCURATE_GEMINI_MODEL = "gemini-2.5-flash-lite"
    FAST_GEMINI_MODEL = "gemini-2.5-flash-lite"

    TEMPERATURE = 0.2
    TOP_P = 0.7


class TaskExecutionConfig:
    SEARCH_COUNT_LIMIT = 3

    TASK_LOG_DIR = Path(ROOT_DIR) / "logs"
    TASK_LOG_DIR.mkdir(parents=True, exist_ok=True)


class EmbedderConfig:
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
    SEPARATORS = ["\n\n\n", "\n\n", "\n", ".", "!", "?"]


class VectorConfig:
    VECTORSTORE_DIR_PATH = Path(DATA_DIR) / "vectorstore"
    VECTORSTORE_DIR_PATH.mkdir(parents=True, exist_ok=True)

    COLLECTION_NAME_BOOKS = "books"

    # Retrieval parameters (number of chunks to retrieve for a query)
    RETRIEVAL_TOP_K = 200


class AppConfig:
    # API settings
    API_HOST = "0.0.0.0"
    API_PORT = 8100
    API_TITLE = "Cliston"
    API_VERSION = "0.1.0"

    # Logging
    LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
