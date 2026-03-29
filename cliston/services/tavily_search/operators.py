import re

from services.tavily_search.client import get_client
from services.tavily_search.models import SearchDepth, Topic
from utils import asyncify


def sanitize_search_result(text: str) -> str:
    """
    Scrubs potential prompt injection markers and structural
    hijacking attempts from raw web text.
    """
    if not text:
        return ""

    # 1. Block common 'System' or 'Role' markers used in injections
    forbidden_sequences = [
        "<|system|>",
        "<|user|>",
        "<|assistant|>",
        "### Instruction",
        "### Response",
        "NEW_RULE:",
        "IGNORE_PREVIOUS",
        "SYSTEM_NOTE:",
        "ADMIN_ACCESS:",
        '"action":',
        '"action_input":',
        "action input:",
        "using tool:",
        "```json",
        "## your task",
        "i'm sorry, but i'm sorry",
        "thought:",
        "action:",
    ]

    sanitized = text
    for seq in forbidden_sequences:
        # We replace with a neutral marker to maintain context
        # without triggering the LLM's instruction-following logic.
        sanitized = re.sub(re.escape(seq), "[REDACTED_MARKER]", sanitized, flags=re.IGNORECASE)

    # 2. Limit extreme length to prevent 'Resource Exhaustion' or
    # 'Context Stuffing' attacks (e.g., 15k characters per snippet)
    return sanitized[:15000]


@asyncify
def web_search(
    query: str,
    topic: Topic,
    days: int = 365,
    # not in tool args
    search_depth: SearchDepth = SearchDepth.ADVANCED,
    max_results: int = 10,
    timeout: int = 30,
) -> str:
    """
    Searches the internet for real-time information and news.
    Args:
        query: The search query string.
        topic: The topic of the search.
        search_depth: The depth of the search.
        max_results: The maximum number of results to return.
        days: The number of days to look back for the search.
        timeout: The timeout for the search in seconds.
    """

    search_result = get_client().search(
        query=query,
        max_results=max_results,
        search_depth=search_depth.value,
        topic=topic.value,
        days=days,
        timeout=timeout,
    )

    clean_text = sanitize_search_result(text=str(search_result))

    return clean_text
