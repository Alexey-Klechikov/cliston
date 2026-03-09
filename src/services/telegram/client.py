import os

from telegram import Bot

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN")  # type: ignore


_telegram_bot_client: Bot | None = None


def get_telegram_client() -> Bot:
    """Singleton for Telegram Bot client."""
    global _telegram_bot_client
    if _telegram_bot_client is None:
        _telegram_bot_client = Bot(token=TELEGRAM_BOT_TOKEN)
    return _telegram_bot_client
