---
description: "Use when editing FastAPI code under cliston/api/. Defines router/operator boundaries, current task semantics, and API-layer style."
applyTo: "cliston/api/**"
---
# API Layer Guidelines

- Keep `cliston/api/` as the request boundary: routers, API-facing Pydantic models, status codes, and HTTP-specific exception shaping belong here.
- Keep routers thin. Parse the request, call an operator, and shape the response; orchestration and long-running work belong in `operators.py`.
- Use each package's `models.py` for request and response schemas instead of passing raw dictionaries deeper into the stack.
- Preserve the current contracts unless the task explicitly changes them: `POST /task/execute` returns a submit envelope, `GET /task/{task_id}` reads in-memory task state, and `/rag/extract_character_profile` owns the HTTP shape while loading and retrieval stay below this layer.
- Raise or translate HTTP-specific errors near this layer. Let lower-level integrations report domain failures as plain Python errors unless the endpoint needs a different status code.
- Use clear endpoint-specific names such as `task_state`, `task_input`, or `character_profile_response`.
- If you change a public route, response model, or status semantic, update `README.md` and often `AGENTS.md` in the same task.
