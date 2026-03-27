import asyncio
import json
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

SRC_DIR = Path(__file__).resolve().parent / "cliston"
sys.path.insert(0, str(SRC_DIR))

from cliston.services.telegram.models import ReactionEmoji
from cliston.services.telegram.operators import (
    add_message_reaction,
    get_chat_updates,
    list_chats,
    list_users,
    send_message,
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8100")
EMBADDER_SERVICE_URL = os.getenv("EMBEDDER_SERVICE_URL", "http://localhost:8009")


MODE = "task_execute"  # "send", "updates", "chats", "users", "reaction", "task_execute",
# "embed", "extract_character_profile"

# Telegram
CHAT_ID = 1763158218
TEXT = "Hello from example_requests"
MESSAGE_ID = 3085
REACTION = ReactionEmoji.THUMBS_UP

# Task
# TASK_MESSAGE = "Find me the latest price of OMX30 index"
TASK_MESSAGE = "Tell me the weather in Stockholm right now"
# TASK_MESSAGE = "Tell me more about the weather. Wind speed, humidity, and more"
# TASK_MESSAGE ="Tell me what Active Share is"

TASK_POLL_INTERVAL_SECONDS = 20.0
TASK_POLL_TIMEOUT_SECONDS = 180.0


async def ping_telegram() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN env var is not set")

    if MODE == "updates":
        result = await get_chat_updates()
        for update in result:
            print(json.dumps(update.model_dump(mode="json"), indent=2))

    elif MODE == "chats":
        result = await list_chats()
        for chat in result:
            print(json.dumps(chat.model_dump(mode="json"), indent=2))
    elif MODE == "users":
        result = await list_users(chat_id=CHAT_ID)
        for user in result:
            print(json.dumps(user.model_dump(mode="json"), indent=2))
    elif MODE == "reaction":
        result = await add_message_reaction(
            chat_id=CHAT_ID,
            message_id=MESSAGE_ID,
            emoji=REACTION,
        )
        print(json.dumps({"ok": result}, indent=2))
    else:
        result = await send_message(chat_id=CHAT_ID, text=TEXT)
        print(json.dumps(result.model_dump(mode="json"), indent=2))


async def test_task_execute() -> None:
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=600.0) as client:
        submit_response = await client.post(
            "/task/execute",
            json={"user_message": TASK_MESSAGE},
        )
        submit_response.raise_for_status()
        task = submit_response.json()
        print(json.dumps(task, indent=2))

        task_id = task["task_id"]
        deadline = time.monotonic() + TASK_POLL_TIMEOUT_SECONDS

        while True:
            await asyncio.sleep(TASK_POLL_INTERVAL_SECONDS)

            status_response = await client.get(
                f"/task/{task_id}",
            )
            status_response.raise_for_status()
            status_payload = status_response.json()
            print(json.dumps(status_payload, indent=2))

            status_value = status_payload.get("status")
            if status_value in {"completed", "failed"}:
                break

            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for task {task_id}")


async def test_extract_character_profile(character_name: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=600.0) as client:
        response = await client.get(
            "/rag/extract_character_profile",
            params={"character_name": character_name},
        )
        response.raise_for_status()
        print(response.json())


if __name__ == "__main__":
    if MODE == "task_execute":
        asyncio.run(test_task_execute())
    elif MODE == "extract_character_profile":
        asyncio.run(test_extract_character_profile(character_name="MTB"))
    else:
        asyncio.run(ping_telegram())
