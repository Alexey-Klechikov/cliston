from .client import get_telegram_client
from .models import TelegramConfig
from typing import Dict, Any

async def send_message(config: TelegramConfig, chat_id: int, text: str) -> Dict[str, Any]:
    client = get_telegram_client(config)
    response = await client.post("/sendMessage", json={"chat_id": chat_id, "text": text})
    return response.json()

# Add more operator functions as needed for webhook handling, etc.
