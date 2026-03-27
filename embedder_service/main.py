import logging
import sys
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from embedder_service.config import AppConfig, ModelConfig

# Configure logging
log_level = AppConfig.LOG_LEVEL
log_format = "%(asctime)s [%(levelname)s] %(message)s"
if log_level.upper() == "DEBUG":
    log_format = "%(asctime)s [%(levelname)s] [%(name)s] - %(message)s"

logging.basicConfig(level=getattr(logging, log_level), format=log_format)

app = FastAPI(title=AppConfig.API_TITLE, version=AppConfig.API_VERSION)

_model: SentenceTransformer | None = None


def _configure_third_party_logging() -> None:
    # Reduce HF/Transformers noise in application logs.
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

    try:
        from transformers import logging as hf_logging

        hf_logging.set_verbosity_error()
    except Exception:
        pass

    try:
        from huggingface_hub import logging as hf_hub_logging

        hf_hub_logging.set_verbosity_error()
    except Exception:
        pass


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logging.info("Loading embedding model: %s", ModelConfig.EMBEDDING_MODEL)
        started_at = time.perf_counter()

        try:
            _model = SentenceTransformer(
                ModelConfig.EMBEDDING_MODEL,
                cache_folder=str(ModelConfig.CACHE_DIR),
                local_files_only=True,
            )
            logging.info(
                "Loaded embedding model from cache: %s in %.2fs",
                ModelConfig.CACHE_DIR,
                time.perf_counter() - started_at,
            )
        except Exception as e:
            logging.info("Model not found locally (%s). Downloading to: %s", e, ModelConfig.CACHE_DIR)
            _model = SentenceTransformer(ModelConfig.EMBEDDING_MODEL, cache_folder=str(ModelConfig.CACHE_DIR))
            logging.info(
                "Model downloaded and cached at: %s in %.2fs",
                ModelConfig.CACHE_DIR,
                time.perf_counter() - started_at,
            )

        embedding_dimension = _model.get_sentence_embedding_dimension()
        logging.info(
            "Embedding model ready: model=%s dimension=%s",
            ModelConfig.EMBEDDING_MODEL,
            embedding_dimension,
        )

    return _model


_configure_third_party_logging()


class EmbedRequest(BaseModel):
    texts: list[str]


@app.post("/embed")
def embed(request: EmbedRequest) -> dict[str, list[list[float]]]:
    if not request.texts:
        logging.info("Embed request received with 0 texts")
        return {"embeddings": []}

    logging.info("Embed request received")

    model = _get_model()
    started_at = time.perf_counter()
    vectors = model.encode(request.texts, normalize_embeddings=True, show_progress_bar=False)
    duration_seconds = time.perf_counter() - started_at

    embeddings = [vector.tolist() for vector in vectors]

    logging.info("Embed request completed: duration_seconds=%.3f", duration_seconds)

    return {"embeddings": embeddings}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    logging.info("Starting %s v%s", AppConfig.API_TITLE, AppConfig.API_VERSION)
    logging.info("Server will be available at http://%s:%s", AppConfig.API_HOST, AppConfig.API_PORT)

    uvicorn.run(
        app,
        host=AppConfig.API_HOST,
        port=AppConfig.API_PORT,
        reload=False,
        log_level=AppConfig.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
