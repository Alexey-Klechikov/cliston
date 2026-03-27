import asyncio
import logging

from google.genai import types
from services.genai.client import get_client


async def ask(
    model: str,
    document_context: str,
    user_prompt: str,
    system_prompt: str | None = None,
) -> str:
    logging.debug(f"Ask Google GenAi: {user_prompt}")

    response = await asyncio.to_thread(
        get_client().models.generate_content,
        model=model,
        contents=[types.Part.from_text(text=i) for i in [document_context, user_prompt]],
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.MEDIUM),
        ),
    )
    return response.text or ""
