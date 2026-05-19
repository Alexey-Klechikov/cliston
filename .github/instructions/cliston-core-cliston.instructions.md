---
description: "Use when editing the top-level Cliston orchestrator under cliston/core/cliston/. Covers delegation flow and prompt/loop boundaries."
applyTo: "cliston/core/cliston/**"
---
# Cliston Agent Guidelines

- `agent.py` owns `call_cliston(user_query, task_id)` and the orchestration loop; `config.py` owns prompt text and `ITERATION_BUDGET`.
- Cliston delegates only through tool calls: `call_mtb_for_research` for web research and `call_garm_for_browser_control` for browser automation and tactical-manual replay.
- `get_or_create_chat(...)` is intentionally persistent for the current day in this agent. Do not add `is_single_use=True` unless you are deliberately changing Cliston memory behavior.
- The request is reset each iteration to the next `ITERATION_COUNT` part plus tool results. If you change that shape, validate the whole tool-call loop.
- Tool failures are intentionally serialized back to the model through broad `try/except` wrappers in `_process_tools_calls`; Cliston uses those strings to decide whether to reroute or summarize partial success.
- Cliston does not throttle between iterations. Do not add `asyncio.sleep(...)` unless the behavior change is deliberate and validated.
- Keep the system prompt assembled entirely in `config.py`; do not scatter prompt fragments through `agent.py`.
