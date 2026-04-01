# Cliston — Workspace Instructions

Cliston is a FastAPI service that routes natural-language queries through a hierarchy of three Gemini-powered AI agents (Cliston → MTB / Garm). It includes a RAG pipeline over a local book corpus (ChromaDB + external embedder sidecar) and Playwright-based browser automation with SQLite-backed tactical replay.

## Build & Run

```bash
uv sync                         # install deps (Python 3.12 only)
uv run python cliston/main.py   # local dev; API at http://0.0.0.0:8100/docs

docker compose up --build       # full stack (chat-service only; embedder runs separately)
docker compose down
```

Required env vars in `.env`: `GOOGLE_STUDIO_KEY`, `TAVILY_API_KEY`, `TELEGRAM_BOT_TOKEN`.
Optional: `EMBEDDER_URL`, `EMBEDDER_TIMEOUT_SECONDS`, `EMBEDDER_BATCH_SIZE`.

## Architecture

```
cliston/
  api/          # FastAPI routers: /health, /task, /rag
  core/
    cliston/    # Orchestrator agent (gemini-2.5-flash-lite, budget=3, retains daily chat)
    mtb/        # Web search agent — Tavily, is_single_use=True (fresh chat per call)
    garm/       # Browser automation agent — Playwright Firefox, tactical manual replay
  services/
    genai/      # Singleton Gemini client; chats keyed {agent_id}_{YYYY-MM-DD}
    embedder/   # HTTP client to embedder sidecar (port 8009, sync httpx)
    vectors/    # ChromaDB at cliston/data/vectorstore/, collection "books"
    document/   # PDF/docx loader + recursive char splitter (chunk=1500, overlap=150)
    playwright/ # Firefox session; headless=False — requires a display
    tavily_search/
    telegram/
    logging/    # Writes logs to cliston/logs/ as {date}_{time}_{status}.txt
```

**Garm tactical manuals** — stored in SQLite (`cliston/data/tables/garm_intelligence.db`), PK = `(domain, objective)`. Replay requires an exact objective string match.

## Import Convention

`main.py` inserts `sys.path` so two styles coexist:
- Agent files use `from cliston.core.xxx import ...` (fully qualified)
- Routers use `from api.xxx import ...` (relative-to-root)

**Always match the style of the file you're editing.** Mixing styles in a new file will fail depending on CWD. Prefer the fully qualified `cliston.` prefix for new code.

## Key Patterns

- **Config**: Plain classes with class-level `os.getenv()` constants — not Pydantic `BaseSettings`.
- **Async/sync bridge**: Gemini SDK and embedding client are synchronous; always wrap in `asyncio.to_thread()`.
- **Task state is in-memory only** — `_task_states` dict is lost on restart; no persistence.
- **Dirs created at import time** — `Path.mkdir()` calls in `__init__.py` and config class bodies are side effects; don't be surprised by automatic directory creation.

## Known Pitfalls

- **`headless=False`** — Playwright will crash in headless/CI environments. Change to `True` for server use.
- **Embedder not in docker-compose** — the `embedder-service` must run separately; RAG will silently time out without it.
- **`pytest pythonpath = ["src"]`** — wrong path; tests need `cliston/` on the path. Run pytest from the workspace root with `PYTHONPATH=.` or fix `pyproject.toml` before adding tests.
- **`POST /task/execute` blocks** — despite returning 202, it awaits the full agent chain; no real async task queue.
- **Gemini model names** — verify model strings against available API models; `gemini-3.1-flash-lite-preview` in RAG config may be incorrect.

## Coding Guidelines

- **Simplicity first**: minimum code that solves the problem. No speculative features or abstractions.
- **Surgical changes**: touch only what the request requires; don't refactor adjacent code.
- **No over-engineering**: no error handling for impossible scenarios, no helpers for one-time operations.
- **State assumptions explicitly** before implementing; surface trade-offs rather than picking silently.
