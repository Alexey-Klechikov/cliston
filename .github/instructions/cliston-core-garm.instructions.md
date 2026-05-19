---
description: "Use when editing the Garm browser-automation agent under cliston/core/garm/. Covers tactical-manual replay, storage, and autonomous browsing."
applyTo: "cliston/core/garm/**"
---
# Garm Agent Guidelines

- `agent.py` owns `call_garm_browser_control(domain, tactical_manual_name, objective, task_id)` plus the replay and autonomous-planning loops.
- `config.py` owns the prompt text, `STEPS_BUDGET`, and `REPORT_SCHEMA`; `tactics_manager.py` and `tactics_storage.py` own manual parsing, scoring, and SQLite persistence.
- Keep browser transport and session logic in `cliston/services/playwright/**`, not inside the agent package.
- Domains are normalized before lookup and storage. Tactical manuals persist in `cliston/data/tables/garm_intelligence.db` and are selected only when reliability is high enough and steps exist.
- Replay runs before autonomous planning when a matching manual exists. Do not skip the post-replay `browser_inspect`; Garm uses it to decide whether the replay already satisfied the objective.
- `close_browser()` must stay in `finally` blocks. Garm intentionally throttles with `asyncio.sleep(1)` between steps and iterations.
- Successful manual updates depend on verified successful steps in `execution_trace`. If you change tool-call formatting or placeholders such as `[QUERY]` and `[TICKER]`, update both serialization and replay parsing.
