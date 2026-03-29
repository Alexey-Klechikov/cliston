from enum import StrEnum


class Topic(StrEnum):
    GENERAL = "general"
    NEWS = "news"
    FINANCE = "finance"


class SearchDepth(StrEnum):
    BASIC = "basic"
    ADVANCED = "advanced"
    FAST = "fast"
    ULTRA_FAST = "ultra-fast"
