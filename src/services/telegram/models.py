from pydantic import BaseModel, Field

class TelegramConfig(BaseModel):
    token: str = Field(..., description="Telegram bot token")
