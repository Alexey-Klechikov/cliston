from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class Chat(BaseModel):
    id: int
    type: str
    title: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class User(BaseModel):
    id: int
    is_bot: bool
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None


class ChatMessage(BaseModel):
    message_id: int
    from_user: User = Field(..., alias="from")
    chat: Chat
    date_unix: int = Field(..., alias="date")
    date_dt: datetime | None = None
    text: str | None = None
    entities: list[dict] | None = None
    channel_chat_created: bool
    delete_chat_photo: bool
    group_chat_created: bool
    supergroup_chat_created: bool

    @model_validator(mode="after")
    def set_date_dt(self):
        if self.date_dt is None:
            self.date_dt = datetime.fromtimestamp(self.date_unix)
        return self


class ChatUpdate(BaseModel):
    update_id: int = Field(..., description="Unique identifier for the update")
    message: ChatMessage = Field(..., description="The message object associated with the update")


class ReactionEmoji(str, Enum):
    HEART = "❤"
    THUMBS_UP = "👍"
    THUMBS_DOWN = "👎"
    FIRE = "🔥"
    SMILING_FACE_WITH_HEARTS = "🥰"
    CLAPPING_HANDS = "👏"
    GRINNING_FACE_WITH_SMILING_EYES = "😁"
    THINKING_FACE = "🤔"
    EXPLODING_HEAD = "🤯"
    FACE_SCREAMING_IN_FEAR = "😱"
    FACE_WITH_SYMBOLS_ON_MOUTH = "🤬"
    CRYING_FACE = "😢"
    PARTY_POPPER = "🎉"
    STAR_STRUCK = "🤩"
    FACE_VOMITING = "🤮"
    PILE_OF_POO = "💩"
    FOLDED_HANDS = "🙏"
    OK_HAND = "👌"
    DOVE = "🕊"
    CLOWN_FACE = "🤡"
    YAWNING_FACE = "🥱"
    WOOZY_FACE = "🥴"
    SMILING_FACE_WITH_HEART_EYES = "😍"
    WHALE = "🐳"
    HEART_ON_FIRE = "❤‍🔥"
    NEW_MOON_FACE = "🌚"
    HOT_DOG = "🌭"
    HUNDRED_POINTS = "💯"
    ROLLING_ON_THE_FLOOR_LAUGHING = "🤣"
    HIGH_VOLTAGE = "⚡"
    BANANA = "🍌"
    TROPHY = "🏆"
    BROKEN_HEART = "💔"
    FACE_WITH_RAISED_EYEBROW = "🤨"
    NEUTRAL_FACE = "😐"
    STRAWBERRY = "🍓"
    BOTTLE_WITH_POPPING_CORK = "🍾"
    KISS_MARK = "💋"
    MIDDLE_FINGER = "🖕"
    SMILING_FACE_WITH_HORNS = "😈"
    SLEEPING_FACE = "😴"
    LOUDLY_CRYING_FACE = "😭"
    NERD_FACE = "🤓"
    GHOST = "👻"
    MAN_TECHNOLOGIST = "👨‍💻"
    EYES = "👀"
    JACK_O_LANTERN = "🎃"
    SEE_NO_EVIL_MONKEY = "🙈"
    SMILING_FACE_WITH_HALO = "😇"
    FEARFUL_FACE = "😨"
    HANDSHAKE = "🤝"
    WRITING_HAND = "✍"
    HUGGING_FACE = "🤗"
    SALUTING_FACE = "🫡"
    SANTA_CLAUS = "🎅"
    CHRISTMAS_TREE = "🎄"
    SNOWMAN = "☃"
    NAIL_POLISH = "💅"
    ZANY_FACE = "🤪"
    MOAI = "🗿"
    COOL_BUTTON = "🆒"
    HEART_WITH_ARROW = "💘"
    HEAR_NO_EVIL_MONKEY = "🙉"
    UNICORN = "🦄"
    FACE_BLOWING_A_KISS = "😘"
    PILL = "💊"
    SPEAK_NO_EVIL_MONKEY = "🙊"
    SMILING_FACE_WITH_SUNGLASSES = "😎"
    ALIEN_MONSTER = "👾"
    MAN_SHRUGGING = "🤷‍♂"
    PERSON_SHRUGGING = "🤷"
    WOMAN_SHRUGGING = "🤷‍♀"
    POUTING_FACE = "😡"


class MessageReaction(BaseModel):
    chat: Chat
    message_id: int
    user: User | None = None
    actor_chat: Chat | None = None
    date_unix: int = Field(..., alias="date")
    old_reaction: list[dict] = Field(default_factory=list)
    new_reaction: list[dict] = Field(default_factory=list)


class MessageReactionUpdate(BaseModel):
    update_id: int = Field(..., description="Unique identifier for the update")
    message_reaction: MessageReaction = Field(..., description="Reaction update payload")
