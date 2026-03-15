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


class AppConfig:
    # API settings
    API_HOST = "0.0.0.0"
    API_PORT = 8100
    API_TITLE = "Cliston"
    API_VERSION = "0.1.0"

    # Logging
    LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
