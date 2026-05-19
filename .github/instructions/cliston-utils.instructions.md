---
description: "Use when editing shared helpers in cliston/utils.py or cliston/core/utils.py. Defines the expected scope for small utilities in this repo."
applyTo:
  - "cliston/utils.py"
  - "cliston/core/utils.py"
---
# Utils Guidelines

- Keep utility modules small and generic within their owning layer.
- `cliston/utils.py` is for repo-wide helpers such as `asyncify` that adapt sync work into async call sites without adding product rules.
- `cliston/core/utils.py` is for shared agent-loop helpers such as response-text extraction, function-call parsing, and iteration markers. Keep it focused on generic agent plumbing, not one agent's policy.
- If a helper depends on one external integration, it probably belongs in `cliston/services/**`; if it depends on one agent's prompt or workflow, it probably belongs in that agent package.
- Preserve simple, explicit inputs and outputs. These helpers are hot paths in the agent loops and should stay easy to reason about.
