from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent
ENV_FILE = ROOT_DIR.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ASK_GEMINI_MODEL: str = "gemini-3.1-flash-lite-preview"
    SEARCH_COUNT_LIMIT: int = 3
    EMBEDDER_URL: str = "http://0.0.0.0:8009"
    EMBEDDER_TIMEOUT_SECONDS: float = 120
    EMBEDDER_BATCH_SIZE: int = 32

    # Chunk size in characters
    CHUNK_SIZE: int = 1500
    CHUNK_OVERLAP: int = 150

    # Vectorstore collection name
    COLLECTION_NAME_BOOKS: str = "books"

    # Retrieval parameters (number of chunks to retrieve for a query)
    RETRIEVAL_TOP_K: int = 200

    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8100
    API_TITLE: str = "Cliston"
    API_VERSION: str = "0.1.0"

    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL


settings = Settings()
