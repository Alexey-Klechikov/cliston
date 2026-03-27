import os
from pathlib import Path

EMBEDDER_ROOT = Path(__file__).parent


class ModelConfig:
    CACHE_DIR = Path(os.getenv("EMBEDDER_CACHE_DIR", EMBEDDER_ROOT / "loaded_models"))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    EMBEDDING_MODEL = "intfloat/multilingual-e5-base"  # Local multilingual embedding: 1.1GB, 768 dimensions


class AppConfig:
    # API settings
    API_HOST = "0.0.0.0"
    API_PORT = 8009
    API_TITLE = "Embedder Service"
    API_VERSION = "0.1.0"

    # Logging
    LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
