---
description: "Use when editing integrations under cliston/services/. Defines service boundaries, lifecycle patterns, and configuration expectations."
applyTo: "cliston/services/**"
---
# Services Guidelines

- Keep `cliston/services/` for external integrations and infrastructure wrappers: Gemini, Tavily, Playwright, remote embeddings, vector storage, document parsing, Telegram, and task logging belong here.
- Follow the existing split where a service package may contain `client.py`, `models.py`, `operators.py`, and `session.py`. Keep transport details in clients and sessions, typed payloads in models, and reusable integration flows in operators.
- Preserve the current lifecycle patterns unless the task explicitly changes them: singleton-style clients for Gemini, Tavily, and Telegram; a reusable sync HTTP client inside `EmbeddingService`; and `asyncify` around blocking document, Tavily, or Chroma work.
- Prefer adding shared runtime configuration through `cliston/settings.py`, but preserve existing direct secret reads such as `GOOGLE_STUDIO_KEY`, `TAVILY_API_KEY`, and `TELEGRAM_BOT_TOKEN` unless you migrate the whole contract.
- Keep agent prompts and request orchestration out of services. Services should return reusable integration results for the API and agent layers.
- Playwright session behavior is part of the service contract. If you change browser type, headless mode, or lifecycle, validate Garm end to end.
- RAG-related services persist local state under `cliston/data/`; if you change that storage contract, update `README.md` and usually `AGENTS.md` too.
