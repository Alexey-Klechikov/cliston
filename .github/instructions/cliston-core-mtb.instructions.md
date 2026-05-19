---
description: "Use when editing the MTB research agent under cliston/core/mtb/. Covers Tavily search flow and single-use chat behavior."
applyTo: "cliston/core/mtb/**"
---
# MTB Agent Guidelines

- `agent.py` owns `call_mtb_for_research(user_query, task_id)` and the Tavily-backed investigation loop; `config.py` owns prompt text and `SEARCH_BUDGET`.
- MTB is intentionally stateless per call. Keep `get_or_create_chat(..., is_single_use=True)` unless you are deliberately changing that isolation.
- `_process_tools_calls` should only execute the `web_search` tool. Raw `topic` strings must still be coerced into the `Topic` enum before calling the Tavily operator.
- MTB does not use screenshots or binary tool results. Keep the data flow text-only.
- If `extract_response_text(...)` is empty, MTB falls back to a hardcoded no-evidence reply. Preserve that behavior unless the caller contract changes too.
- Keep the system prompt assembled in `config.py`; do not inline prompt fragments in the loop.
