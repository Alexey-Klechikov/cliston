from fastapi import Request
from functools import lru_cache
from .models import TelegramConfig
import httpx

@lru_cache(maxsize=1)
def get_telegram_client(config: TelegramConfig):
    """
    Singleton for Telegram HTTP client.
    """
    return httpx.AsyncClient(base_url=f"https://api.telegram.org/bot{config.token}")
