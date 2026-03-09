import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from services.telegram.operators import (
    add_message_reaction,
    get_chat_updates,
    list_chats,
    list_users,
    send_message,
)
from services.telegram.models import ReactionEmoji


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8100")
API_KEY = os.getenv("X_API_KEY")

MODE = "task_execute"  # "send", "updates", "chats", "users", "reaction", "task_execute"

# Telegram
CHAT_ID = 1763158218
TEXT = "Hello from example_requests"
MESSAGE_ID = 3085
REACTION = ReactionEmoji.THUMBS_UP

# Task
TASK_MESSAGE = "Find me the latest price of OMX30 index"


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
    if not API_KEY:
        raise RuntimeError("X_API_KEY env var is not set")

    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=60.0) as client:
        response = await client.post(
            "/task/execute",
            json={"user_message": TASK_MESSAGE},
            headers={"x-api-key": API_KEY},
        )
        response.raise_for_status()
        print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    if MODE == "task_execute":
        asyncio.run(test_task_execute())
    else:
        asyncio.run(ping_telegram())
