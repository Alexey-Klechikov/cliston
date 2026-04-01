---
applyTo: "cliston/core/mtb/**"
---

# MTB Agent — Coding Instructions

MTB is the **web research** sub-agent. It is stateless and receives a fresh chat session on every call.

## Structure

| File | Purpose |
|---|---|
| `agent.py` | Entry point `call_mtb_for_research(user_query, task_id)`. Drives the Tavily search loop. |
| `config.py` | `AgentConfig` — plain class with prompt text and constants. |
| `tools.py` | `call_mtb_for_research_tool` — the GenAI `FunctionDeclaration` Cliston uses to invoke MTB. |

## Iteration Loop

- Budget: `AgentConfig.SEARCH_BUDGET = 4`
- Each turn: send request → check for tool calls → process `web_search` → repeat
- `Topic` enum must be coerced from the raw string argument before calling `web_search` — already handled in `_process_tools_calls`
- Non-`web_search` tool calls are silently skipped (`continue`) — do not raise errors

## Key Constraint: Single-Use Chat

```python
get_or_create_chat(..., is_single_use=True)
```

**This must stay.** MTB gets a completely fresh chat per call — no context is shared between Cliston invocations. Removing `is_single_use=True` would pollute MTB's state with prior unrelated searches.

## Fallback Response

If `extract_response_text(response)` returns empty, MTB returns a hardcoded "no evidence" string rather than an empty result. This is intentional — Cliston interprets an empty string as a silent failure.

## Rules for Editing This Agent

- **Do not add `asyncio.sleep`** — MTB does not need throttling.
- **No screenshot/binary results** — MTB only deals with text from `web_search`. No `bytes` in the response pipeline.
- **System prompt lives in `config.py`** — `TASK` uses `.format(search_budget=...)`, keep that placeholder.
- **Do not add new tools without updating `tools.py`** — Cliston's tool declaration must match.
