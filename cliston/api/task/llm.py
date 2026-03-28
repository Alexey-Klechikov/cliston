import logging
import os

from config import ModelConfig
from crewai import LLM

_llm: LLM | None = None


def get_llm() -> LLM:
    global _llm
    if _llm is None:
        _llm = LLM(
            model=ModelConfig.CREWAI_GEMINI_MODEL,
            api_key=os.getenv("GOOGLE_STUDIO_KEY"),
            temperature=ModelConfig.TEMPERATURE,
            top_p=ModelConfig.TOP_P,
        )
        logging.info("LLM initialized with model: %s", ModelConfig.CREWAI_GEMINI_MODEL)

    return _llm
