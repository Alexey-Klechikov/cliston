# Cliston

Cliston is a FastAPI service that fronts a small multi-agent system inspired by the Hard Luck Hank universe. The top-level Cliston agent decides whether a request should go to MTB for web research, Garm for browser automation, or the local RAG pipeline for character profile extraction from the bundled book corpus.

## Capabilities

- Natural-language task execution through the Cliston orchestration loop.
- Web research through MTB and Tavily-backed search.
- Browser automation and reusable tactical-manual replay through Garm and Playwright.
- Character profile extraction over local Hard-Luck-Hank texts using Chroma-backed retrieval and Gemini summarization.
- Health checks for runtime liveness.

## Architecture

- `cliston/api/`: FastAPI routers plus request-level operators for `health`, `task`, and `rag`.
- `cliston/core/`: Agent configs, orchestration loops, shared tool-call helpers, and Garm's tactical-manual logic.
- `cliston/services/`: Gemini, Tavily, Playwright, embeddings, vector storage, document loading, Telegram, and task logging.
- `cliston/data/`: Source books, persistent vectorstore data, and Garm's SQLite tactical-manual database.
- `cliston/logs/`: Plain-text task transcripts written during task execution.

## Requirements

- Python `3.12.x`
- `uv`
- `GOOGLE_STUDIO_KEY` for Gemini-backed agent and RAG calls
- `TAVILY_API_KEY` for MTB web research
- A reachable embedder service at `EMBEDDER_URL` for RAG/vector search
- Optional `TELEGRAM_BOT_TOKEN` for the helper functions exercised by [example_requests.py](example_requests.py)

`cliston/settings.py` supplies defaults for API host/port, retrieval settings, chunking, and embedder connection details. The API listens on `http://localhost:8100` by default.

## Run Locally

```sh
uv sync --frozen
uv run python cliston/main.py
```

OpenAPI docs are available at `http://localhost:8100/docs`.

If you want to use the RAG endpoint, start an embedder service separately or point `EMBEDDER_URL` at an existing deployment before calling the API.

## Run with Docker Compose

Build and start the API container:

```sh
docker compose up -d --build
```

Stop and remove containers:

```sh
docker compose down
docker builder prune -a -f
docker system prune -a -f
```

The current compose file only defines the Cliston API container. It sets `EMBEDDER_URL=http://embedder-service:8009`, so you still need to provide that embedder service separately or override the environment variable.

## API Overview

### `GET /health`

Returns a simple liveness payload:

```json
{"status": "ok"}
```

### `POST /task/execute`

Submit a user query to the Cliston orchestration flow.

```sh
curl -X POST http://localhost:8100/task/execute \
	-H "Content-Type: application/json" \
	-d '{"user_query":"Find the latest price of OMX30 on avanza.se"}'
```

The response model returns a task id and a `queued` status with HTTP `202`, but the current implementation still awaits the full Cliston run inline before sending that response. After the submit call returns, the result is available through `GET /task/{task_id}` for the lifetime of the current process.

### `GET /task/{task_id}`

Returns the stored task state:

```sh
curl http://localhost:8100/task/<task_id>
```

Responses include the task status plus either `response` or `error`. Task state is held in memory, so it is cleared by process restarts.

### `GET /rag/extract_character_profile`

Extract a character profile from the local book corpus:

```sh
curl "http://localhost:8100/rag/extract_character_profile?character_name=Garm"
```

The first request loads and chunks all supported documents from `cliston/data/books/`, then populates the persistent vector store before retrieval.

## Data and Persistence

- `cliston/data/books/`: local source texts used by the RAG endpoint
- `cliston/data/vectorstore/`: persistent Chroma storage for embedded chunks
- `cliston/data/tables/garm_intelligence.db`: SQLite storage for Garm tactical manuals
- `cliston/logs/`: task transcripts and agent outputs written as plain text

## Example Script

[example_requests.py](example_requests.py) contains manual request flows for the task API, RAG endpoint, and Telegram helper methods. It is the quickest way to smoke-test a request/response change outside the FastAPI docs.
