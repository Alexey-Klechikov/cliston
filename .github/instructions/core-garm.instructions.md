---
applyTo: "cliston/core/garm/**"
---

# Garm Agent — Coding Instructions

Garm is the **browser automation** sub-agent. It is stateless and receives a fresh chat session on every call.
It uses Playwright Firefox to infiltrate websites, and maintains a per-domain SQLite database of reusable "Tactical Manuals".

## Structure

| File | Purpose |
|---|---|
| `agent.py` | Entry point `call_garm_browser_control(domain, objective, task_id)`. Drives the replay + iteration loop. |
| `config.py` | `AgentConfig` — prompt text, `STEPS_BUDGET = 30`, `REPORT_SCHEMA` JSON schema. |
| `tools.py` | `call_garm_browser_control_tool` — the GenAI `FunctionDeclaration` Cliston uses to invoke Garm. |
| `models.py` | `TacticalManual`, `ToolCallTrace` — Pydantic models. |
| `tactics_manager.py` | `TacticsManager` — manual selection, parsing, serialization, update logic. |
| `tactics_storage.py` | Async SQLite CRUD via `aiosqlite`. DB at `cliston/data/tables/garm_intelligence.db`. |

## Execution Flow

```
call_garm_browser_control(domain, objective, task_id)
  ├─ normalize domain (strip protocol/www via _build_homepage_url)
  ├─ load existing manuals from SQLite
  ├─ select best manual (score = token overlap + reliability)
  ├─ _execute_replay_manual()
  │    ├─ if manual found and parseable:
  │    │   replay tool calls → browser_inspect → REPLAY_VALIDATION_PROMPT
  │    └─ else: inject manuals as context + iteration_counter_part(1)
  ├─ autonomous iteration loop (up to STEPS_BUDGET + 2 turns)
  │    each turn: send → tool calls → _process_tools_calls → repeat
  ├─ close_browser() (always, in finally)
  ├─ send CLOSING_SCENE_PROMPT (forced JSON via REPORT_SCHEMA)
  └─ create_or_update_tactical_manual() → archive to SQLite
```

## Browser Tools

| Tool | Arguments | Returns |
|---|---|---|
| `browser_navigate` | `url: str` | `str` result |
| `browser_interact` | `action`, `selector`, `value?` | `str` result |
| `browser_inspect` | _(none)_ | `(screenshot_bytes, str)` |

`browser_inspect` is the only tool that returns a screenshot (`bytes`). Screenshots are appended to the request as `image/jpeg` parts — this is how Garm "sees" the page.

## Tactical Manuals

- Stored in SQLite, PK = `(domain, objective)`.
- `domain` is always normalized (no `https://`, no `www.`) before any storage or lookup.
- Steps are serialized as numbered synthetic tool-call strings: `browser_navigate(url='...')`, `browser_interact(...)`.
- Variable content is replaced with `[QUERY]` or `[TICKER]` placeholders at write time; `TacticsManager._extract_query_value()` resolves the placeholder back at replay time.
- Reliability = `success_count / (success_count + failure_count)`. Manuals below `MIN_RELIABILITY = 0.5` are excluded from injection and selection.
- Only successful runs (result == `"Success"` **and** non-empty verified manual steps) trigger `archive_manual`.

## Replay Validation Protocol

After replaying a manual, Garm always performs a `browser_inspect` and receives `REPLAY_VALIDATION_PROMPT`. It must either:
- **Return directly** if the objective is already satisfied.
- **Navigate to `HOMEPAGE_URL`** as the first tool call if restarting from scratch.

Do not skip the post-replay inspect step — it is required so Garm can assess page state before deciding.

## Report Schema

The `CLOSING_SCENE_PROMPT` forces a structured JSON response matching `AgentConfig.REPORT_SCHEMA`:

```
{
  "result": "Success" | "Failure",
  "data": "<raw telemetry>",
  "summary": "<abrasive summary>",
  "manual": {
    "name": "<generic capability title>",
    "steps": ["browser_navigate(url='...')", ...]
  }
}
```

`manual.name` becomes the `objective` PK in SQLite. Keep it **generic** (e.g. `"Avanza Asset Search"`, not `"Find OMXS30 price"`).

## Rules for Editing This Agent

- **`close_browser()` must fire in a `finally` block** — it must execute even when the loop errors out.
- **`asyncio.sleep(1)` between iterations** — deliberate throttle; do not remove.
- **`REPORT_SCHEMA` lives in `config.py`** — if you add/remove fields, update it there.
- **`TacticsManager` is stateful per call** — `execution_trace` accumulates across the entire session; do not reset it mid-loop.
- **`headless=False`** in the Playwright service — will crash without a display. Change to `True` for server/CI use.
