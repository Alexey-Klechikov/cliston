import logging
import os

from google import genai

_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GOOGLE_STUDIO_KEY"))
        logging.info("GenAI client initialized")

    return _client
