import asyncio
import logging
from datetime import date, datetime
from typing import cast

from google.genai import errors, types
from google.genai.chats import Chat
from pydantic import Field
from services.genai.client import get_client

_chats: dict[str, Chat] = {}
_TRANSIENT_STATUS_CODES = {429, 503}
_MAX_RETRIES = 4


def _create_chat_id(agent_id: str) -> str:
    return f"{agent_id}_{date.today().isoformat()}"


def _get_date_from_chat_id(chat_id: str) -> date | None:
    try:
        date_str = chat_id.rsplit("_", 1)[-1]
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (IndexError, ValueError):
        logging.warning(f"Failed to extract date from chat ID: {chat_id}")
        return None


def _clear_old_chats():
    expired_chat_ids = [i for i in _chats if _get_date_from_chat_id(i) != date.today()]
    for chat_id in expired_chat_ids:
        logging.info(f"Clearing expired chat session: {chat_id}")
        del _chats[chat_id]


def get_or_create_chat(
    agent_id: str,
    model: str,
    config: types.GenerateContentConfig,
    is_single_use: bool = False,
) -> Chat:
    chat_id = _create_chat_id(agent_id)

    if not _chats.get(chat_id) or is_single_use:
        logging.info(f"Creating new chat session for agent '{agent_id}'")
        _chats[chat_id] = get_client().chats.create(model=model, config=config)

        _clear_old_chats()

    return _chats[chat_id]


async def send_message_with_retry(
    chat: Chat,
    message: str | list[types.Part],
    config: types.GenerateContentConfig | None = None,
) -> types.GenerateContentResponse:
    if config is not None:
        config = config.model_copy(
            update={
                "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
            },
        )

    for attempt in range(_MAX_RETRIES + 1):
        try:
            return (
                await asyncio.to_thread(chat.send_message, message, config)
                if config
                else await asyncio.to_thread(chat.send_message, message)
            )
        except errors.ServerError as e:
            if attempt >= _MAX_RETRIES:
                raise

            delay_seconds = min(3, 2**attempt)
            logging.warning(
                "Transient Gemini API error (%s). Retrying in %ss (%s/%s).",
                getattr(e, "status_code", "unknown"),
                delay_seconds,
                attempt + 1,
                _MAX_RETRIES,
            )
            await asyncio.sleep(delay_seconds)

    raise RuntimeError("Unreachable retry loop state")


async def ask(
    model: str,
    user_prompt: str,
    system_prompt: str,
    document_context: list[str] = Field(default_factory=list),
) -> str:
    logging.info(f"Asking Gemini: {user_prompt}")

    response = await asyncio.to_thread(
        get_client().models.generate_content,
        model=model,
        contents=[types.Part.from_text(text=i) for i in document_context + [user_prompt]],
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.MEDIUM),
        ),
    )
    return cast(types.GenerateContentResponse, response).text or ""
