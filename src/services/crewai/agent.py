import logging
import re
from contextvars import ContextVar
from html import unescape
from typing import Any, Sequence
from urllib.parse import parse_qs, quote_plus, urlparse

import httpx
from crewai import Agent
from crewai.tools import tool
from googlesearch import search

from agents import AgentConfig
from services.crewai.llm import get_llm

_search_budget: ContextVar[int | None] = ContextVar("search_budget", default=None)


_BLOCKED_RESULT_HOSTS = {
    "webcache.googleusercontent.com",
    "gstatic.com",
    "www.gstatic.com",
    "accounts.google.com",
    "policies.google.com",
    "ad.doubleclick.net",
}


def _is_good_web_result(url: str) -> bool:
    if not url:
        return False

    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    if host in _BLOCKED_RESULT_HOSTS:
        return False

    if host.endswith(".google.com"):
        return False

    if "news.google.com/rss/articles" in url:
        return False

    lowered = url.lower()
    if lowered.endswith((".js", ".css", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".woff", ".woff2")):
        return False

    return url.startswith("http")


def _collect_web_urls_from_google_html(html: str) -> list[str]:
    urls: list[str] = []

    # Primary extraction pattern used on many SERP versions.
    for candidate in re.findall(r'href="(/url\?q=[^"]+)"', html):
        parsed = urlparse(unescape(candidate))
        target = parse_qs(parsed.query).get("q", [""])[0]
        if target and _is_good_web_result(target):
            urls.append(target)

    # Fallback for SERP variants where direct outbound URLs are embedded in script/data blocks.
    for target in re.findall(r"https://[^\s\"'<>]+", html):
        clean = unescape(target).rstrip(').,;"')
        if _is_good_web_result(clean):
            urls.append(clean)

    deduped_urls: list[str] = []
    seen = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            deduped_urls.append(url)
        if len(deduped_urls) >= 8:
            break

    return deduped_urls


def _collect_web_urls_from_jina_text(text: str) -> list[str]:
    urls: list[str] = []
    for target in re.findall(r"https?://[^\s\"'<>]+", text):
        clean = unescape(target).rstrip(').,;"')
        if _is_good_web_result(clean):
            urls.append(clean)

    deduped_urls: list[str] = []
    seen = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            deduped_urls.append(url)
        if len(deduped_urls) >= 8:
            break

    return deduped_urls


def _collect_web_urls_from_brave_html(html: str) -> list[str]:
    urls: list[str] = []
    for target in re.findall(r'href="(https?://[^"]+)"', html):
        clean = unescape(target).rstrip(').,;"')
        if _is_good_web_result(clean):
            urls.append(clean)

    deduped_urls: list[str] = []
    seen = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            deduped_urls.append(url)
        if len(deduped_urls) >= 12:
            break

    return deduped_urls


def _extract_result_url(result: Any) -> str:
    if isinstance(result, str):
        return result.strip()
    return (getattr(result, "url", "") or "").strip()


def _extract_result_title(result: Any) -> str:
    if isinstance(result, str):
        return ""
    return (getattr(result, "title", "") or "").strip()


def _extract_result_description(result: Any) -> str:
    if isinstance(result, str):
        return ""
    return (getattr(result, "description", "") or "").strip()


def _format_google_results(results: Sequence[Any]) -> str:
    lines = []
    for idx, result in enumerate(results, start=1):
        title = _extract_result_title(result)
        url = _extract_result_url(result)
        description = _extract_result_description(result)
        lines.append(f"[{idx}] {title}\nURL: {url}\nSnippet: {description}")
    return "\n\n".join(lines)


def set_search_budget(max_calls: int | None) -> None:
    _search_budget.set(max_calls)


def run_google_search(search_query: str) -> str:
    """Search Google for information on a specific topic."""
    try:
        results = list(search(search_query, num_results=10, advanced=True))
        filtered_results = [r for r in results if _is_good_web_result(_extract_result_url(r))]

        if filtered_results:
            return _format_google_results(filtered_results[:5])

        # Fallback 1: parse standard Google web SERP HTML.
        google_url = f"https://www.google.com/search?q={quote_plus(search_query)}&num=8&hl=en&pws=0"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        }
        with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
            response = client.get(google_url)
            response.raise_for_status()

        deduped_urls = _collect_web_urls_from_google_html(response.text)[:5]

        if deduped_urls:
            return "\n\n".join([f"[{idx}] URL: {url}" for idx, url in enumerate(deduped_urls, start=1)])

        # Fallback 2: fetch Google SERP via text mirror and extract outbound URLs.
        jina_url = f"https://r.jina.ai/http://www.google.com/search?q={quote_plus(search_query)}&num=8&hl=en&pws=0"
        with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
            jina_response = client.get(jina_url)
            jina_response.raise_for_status()

        jina_urls = _collect_web_urls_from_jina_text(jina_response.text)[:5]
        if jina_urls:
            return "\n\n".join([f"[{idx}] URL: {url}" for idx, url in enumerate(jina_urls, start=1)])

        # Last resort for general usability: return natural web links when Google is blocked.
        brave_url = f"https://search.brave.com/search?q={quote_plus(search_query)}&source=web"
        with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
            brave_response = client.get(brave_url)
            brave_response.raise_for_status()

        brave_urls = _collect_web_urls_from_brave_html(brave_response.text)
        filtered_brave_urls = [url for url in brave_urls if "brave.com" not in url][:5]
        if filtered_brave_urls:
            return "\n\n".join([f"[{idx}] URL: {url}" for idx, url in enumerate(filtered_brave_urls, start=1)])

        return "SEARCH_ERROR: Google returned no parsable web results and fallback search also failed"
    except Exception as exc:
        logging.exception("GoogleSearch failed for query: %s", search_query)
        return f"SEARCH_ERROR: {exc}"


@tool("GoogleSearch")
def managed_search(search_query: str) -> str:
    """Search the internet for information on a specific topic."""
    budget = _search_budget.get()
    if budget is not None:
        if budget <= 0:
            return "SEARCH_ERROR: search budget exceeded (max 3 calls)"
        _search_budget.set(budget - 1)

    return run_google_search(search_query)


_agents: dict[str, Agent] = {}


def get_agent(config: AgentConfig) -> Agent:
    """Return (or create) a singleton Agent for the given config role."""
    if config.role not in _agents:
        tools = []
        if config.allow_search:
            tools.append(managed_search)

        extra_kwargs = {}
        if config.role == "MTB":
            # Keep research focused and avoid repetitive tool loops.
            extra_kwargs = {
                "max_iter": 8,
                "max_execution_time": 45,
                "max_retry_limit": 1,
            }

        _agents[config.role] = Agent(
            role=config.role,
            goal=config.goal,
            backstory=config.backstory,
            tools=tools,
            verbose=config.verbose,
            llm=get_llm(),
            allow_delegation=False,
            **extra_kwargs,
        )

        logging.info("Agent '%s' initialised", config.role)

    return _agents[config.role]
