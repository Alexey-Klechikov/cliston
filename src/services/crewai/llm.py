import logging

from crewai import LLM

from config import ModelConfig

_llm: LLM | None = None


def get_llm() -> LLM:
    global _llm
    if _llm is None:
        _llm = LLM(
            model=ModelConfig.MODEL,
            base_url=ModelConfig.OLLAMA_HOST,
            temperature=ModelConfig.TEMPERATURE,
            top_p=ModelConfig.TOP_P,
            top_k=ModelConfig.TOP_K,
        )
        logging.info("LLM initialized with model: %s", ModelConfig.MODEL)

    return _llm
