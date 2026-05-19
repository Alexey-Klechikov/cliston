# Cliston

## Fast Start
- Use Python 3.12 and `uv`.
- Install dependencies with `uv sync --frozen`.
- Run the API locally with `uv run python cliston/main.py`.
- Use `curl http://localhost:8100/health` as the quickest smoke check after startup.
- `docker compose up -d --build` starts the API container, but the compose file still expects an external embedder service.

## Where To Look First
- [README.md](README.md) for the service overview, API examples, and runtime requirements.
- [cliston/main.py](cliston/main.py) for app startup, middleware, exception handling, and router registration.
- [cliston/api/task/operators.py](cliston/api/task/operators.py) for task execution, in-memory task state, and task log lifecycle.
- [cliston/api/rag/operators.py](cliston/api/rag/operators.py) for document loading, retrieval, and character profile generation.
- [cliston/core/cliston/agent.py](cliston/core/cliston/agent.py) for top-level delegation across MTB and Garm.
- [cliston/core/garm/agent.py](cliston/core/garm/agent.py) and [cliston/core/mtb/agent.py](cliston/core/mtb/agent.py) for the specialized agent loops.
- [cliston/services/vectors/store.py](cliston/services/vectors/store.py) and [cliston/services/document/loader.py](cliston/services/document/loader.py) for RAG persistence and ingestion.
- [.github/hooks/document-observed-knowledge.json](.github/hooks/document-observed-knowledge.json) for the documentation reminder workflow wired into the editor hooks.

## Project Shape
- `cliston/api/**`: FastAPI routers, request/response models, and request-level operators.
- `cliston/core/**`: Agent prompts, orchestration loops, tool declarations, manual replay logic, and shared agent helpers.
- `cliston/services/**`: External integrations and infrastructure wrappers for Gemini, Tavily, Playwright, embeddings, Telegram, logging, and vector storage.
- `cliston/data/**`: Source books, tactical-manual SQLite data, and persistent Chroma vector storage.
- `cliston/logs/**`: Timestamped task execution logs written during task runs.

## Codebase Conventions
- Keep routers thin. Route functions should parse inputs, call an operator, and shape the HTTP response.
- Keep prompt text and tool schemas in each agent package's `config.py` and `tools.py`. `agent.py` should stay focused on loop control and tool execution.
- Shared runtime configuration lives in [cliston/settings.py](cliston/settings.py). Prefer adding durable configuration there instead of scattering new environment reads.
- Some older integration clients still read secrets directly from the environment, especially `GOOGLE_STUDIO_KEY`, `TAVILY_API_KEY`, and `TELEGRAM_BOT_TOKEN`. Preserve those contracts unless you deliberately migrate the callers and documentation together.
- Preserve the existing singleton-style client patterns in `cliston/services/genai/client.py`, `cliston/services/tavily_search/client.py`, and `cliston/services/telegram/client.py` unless the task explicitly changes lifecycle behavior.
- Garm tactical manuals are persisted in `cliston/data/tables/garm_intelligence.db`; domain normalization, replay parsing, and reliability scoring live in `cliston/core/garm/tactics_manager.py` and `cliston/core/garm/tactics_storage.py`.
- RAG depends on a remote embedder via `EMBEDDER_URL`; the local Chroma store persists under `cliston/data/vectorstore/`.

## Validation Notes
- There are no repo-local tests today. `pytest` is installed, but `pyproject.toml` still points pytest's `pythonpath` at `src`, so treat that config as stale.
- Prefer narrow executable checks: `uv run python -m compileall cliston .github/hooks/scripts`, a `/health` smoke request, or an endpoint-specific manual run via [example_requests.py](example_requests.py).
- Validate agent changes against the narrowest affected path: the MTB search loop, the Garm browser/manual replay flow, or the Cliston delegation loop.
- When editing `.github` automation, grep for stale `src/` references before finishing.

## Common Pitfalls
- `POST /task/execute` returns HTTP 202 and a submit envelope, but it currently awaits the full Cliston run inline before responding. Long-running submit requests are normal.
- `GET /task/{task_id}` reads `_task_states` from process memory, so task results disappear on restart.
- `docker-compose.yml` points `EMBEDDER_URL` at `http://embedder-service:8009`, but the compose file does not define that service. Run the embedder separately or override the env var.
- Playwright launches Firefox with `headless=False`; local and container execution need a display-capable environment unless you change that behavior intentionally.
- The first RAG request loads every supported document from `cliston/data/books/`, chunks them, and writes new embeddings into the persistent vector store. Expect a slow first request.
- Task logs accumulate in `cliston/logs/` unless you prune them manually.

## Automation Notes
- `.github/hooks/document-observed-knowledge.json` wires reminder hooks that should track edits under `cliston/`, `.github/`, and the root runtime files.
- Project-specific editor instructions now live under `.github/instructions/` with scopes for the API layer, shared services, shared utilities, settings, and the three core agent packages.
- [example_requests.py](example_requests.py) is a manual smoke-test script for the task API, Telegram helpers, and the RAG endpoint. Keep it runnable when request/response shapes change.
