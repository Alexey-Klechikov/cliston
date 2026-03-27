from services.telegram.client import get_telegram_client
from services.telegram.models import Chat, ChatMessage, ChatUpdate, ReactionEmoji, User
from telegram import ReactionTypeEmoji


async def get_chat_updates(chat_id: int | None = None) -> list[ChatUpdate]:
    bot = get_telegram_client()
    updates = await bot.get_updates()
    if chat_id is not None:
        updates = [i for i in updates if i.effective_chat and i.effective_chat.id == chat_id]
    return [ChatUpdate.model_validate(i.to_dict()) for i in updates]


async def list_chats() -> list[Chat]:
    bot = get_telegram_client()
    updates = await bot.get_updates()

    chats_by_id: dict[int, Chat] = {}
    for update in updates:
        chat = update.effective_chat
        if chat is None:
            continue
        chats_by_id[chat.id] = Chat.model_validate(chat.to_dict())

    return list(chats_by_id.values())


async def list_users(chat_id: int | None = None) -> list[User]:
    bot = get_telegram_client()
    updates = await bot.get_updates()

    users_by_id: dict[int, User] = {}
    for update in updates:
        if chat_id is not None and update.effective_chat and update.effective_chat.id != chat_id:
            continue
        user = update.effective_user
        if user is None:
            continue
        users_by_id[user.id] = User.model_validate(user.to_dict())

    return list(users_by_id.values())


async def send_message(chat_id: int, text: str) -> ChatMessage:
    bot = get_telegram_client()
    message = await bot.send_message(chat_id=chat_id, text=text)
    return ChatMessage.model_validate(message.to_dict())


async def add_message_reaction(chat_id: int, message_id: int, emoji: ReactionEmoji, is_big: bool = False) -> bool:
    bot = get_telegram_client()
    reaction = ReactionTypeEmoji(emoji=emoji.value)
    return await bot.set_message_reaction(chat_id=chat_id, message_id=message_id, reaction=[reaction], is_big=is_big)
