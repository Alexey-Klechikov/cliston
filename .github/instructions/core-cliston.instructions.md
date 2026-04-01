---
applyTo: "cliston/core/cliston/**"
---

# Cliston Agent — Coding Instructions

Cliston is the **orchestrating butler** agent. It receives user queries, delegates to sub-agents, and synthesizes the final response.

## Structure

| File | Purpose |
|---|---|
| `agent.py` | Entry point `call_cliston(user_query, task_id)`. Drives the iteration loop and calls sub-agents via tool calls. |
| `config.py` | `AgentConfig` — plain class with all prompt text and constants. |

## Iteration Loop

- Budget: `AgentConfig.ITERATION_BUDGET = 3`
- Each turn: send request → check for tool calls → process → repeat
- Loop terminates when no tool calls are returned or the budget is exhausted
- Request is restarted each iteration as `[iteration_counter_part(i+2, budget)]` — only the counter and tool results are carried forward, not the full history

## Sub-agent Tools

| Tool name | Calls | When to dispatch |
|---|---|---|
| `call_mtb_for_research` | `call_mtb_for_research(user_query)` | Web research, factual verification, real-time data |
| `call_garm_for_browser_control` | `call_garm_browser_control(domain, objective)` | URLs, UI interaction, live DOM telemetry |

`domain` is a bare hostname — no protocol prefix (e.g. `"avanza.se"`, not `"https://avanza.se"`).

## Error Handling

Both sub-agent calls are wrapped in broad `try/except` in `_process_tools_calls`. Caught exceptions are serialized as a string result and returned to the LLM so it can decide how to recover — **do not remove this wrapper**.

## Rules for Editing This Agent

- **Chat is persistent** — `get_or_create_chat` reuses the same session for an entire calendar day. Do not add `is_single_use=True`.
- **No `asyncio.sleep`** — Cliston does not throttle between iterations; only Garm does.
- **System prompt comes entirely from `AgentConfig.get_system_prompt()`** — do not inline prompt snippets in `agent.py`. Edit `config.py` instead.
- **Config structure**: `ROLE`, `PROFILE`, `BACKSTORY`, `TASK`, `EXPECTED_OUTPUT` — all plain strings joined by `get_system_prompt()`. `TASK` uses `.format(iteration_budget=...)` — keep that placeholder when editing.
