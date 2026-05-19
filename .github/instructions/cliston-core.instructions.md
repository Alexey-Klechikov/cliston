---
description: "Use when editing shared agent scaffolding in cliston/core/models.py or cliston/core/utils.py. Covers cross-agent contracts and helper boundaries."
applyTo:
  - "cliston/core/models.py"
  - "cliston/core/utils.py"
---
# Core Shared Guidelines

- Keep `cliston/core/models.py` and `cliston/core/utils.py` limited to cross-agent contracts and generic helper functions used by Cliston, MTB, and Garm.
- Shared models should represent tool calls or other neutral data structures, not one agent's prompt policy or service lifecycle.
- Shared utils should handle response parsing, function-call extraction, or iteration markers; agent-specific routing decisions belong in the owning agent package.
- When changing a shared contract, update every caller in `cliston/core/**` and the matching tool declarations in the same change.
- Preserve simple, explicit inputs and outputs. These helpers sit in the middle of the orchestration loop and should stay easy to serialize, log, and reason about.
