---
description: "Use when editing cliston/settings.py. Defines what belongs in shared runtime settings and how env-backed config should stay predictable."
applyTo: "cliston/settings.py"
---
# Settings Guidelines

- Keep `cliston/settings.py` for shared runtime configuration used across the FastAPI app and multiple services.
- Prefer sane local defaults so the module stays importable in development, but add required env-backed fields when the whole app truly depends on them.
- Group related settings together and name them after the external contract they configure, such as `EMBEDDER_URL`, `API_PORT`, or `RETRIEVAL_TOP_K`.
- When adding a new reusable setting, route call sites through `settings` instead of adding more scattered `os.getenv(...)` reads.
- If a legacy integration still reads its own secret directly from the environment, either preserve that contract or migrate all call sites and documentation in the same change.
- Changes here usually require `README.md` and sometimes `AGENTS.md` updates because setup and runtime behavior are affected.
