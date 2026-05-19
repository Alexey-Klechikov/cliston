---
description: "Use when deciding whether durable repository knowledge should update AGENTS.md, README.md, or both. Provides concrete examples for documentation updates."
applyTo:
  - "AGENTS.md"
  - "README.md"
---
# Documentation Update Examples

- Update both `AGENTS.md` and `README.md` when a change creates a durable contributor workflow and also changes service-facing behavior or architecture.
- Example for both: adding a new middleware or logging flow that introduces a contributor pitfall and also changes request handling behavior worth documenting.
- Example for both: adding a new supported report type that requires new generation flow notes for contributors and changes the public service capabilities.
- Update only `AGENTS.md` when the fact mainly affects how contributors should work in the repo.
- Example for `AGENTS.md` only: a new cache-clearing requirement in tests, a mocking pitfall, a fixture convention, or a hook/instruction workflow that changes how contributors should edit the repo.
- Example for `AGENTS.md` only: a middleware ordering pitfall that can break tests or request context initialization.
- Update only `README.md` when the fact mainly affects what the service does or how an operator/user understands or runs it.
- Example for `README.md` only: a new endpoint, supported report behavior, deployment/runtime prerequisite, or infrastructure dependency that changes service expectations.
- If a change is temporary debugging noise, one-off migration detail, or implementation trivia with no lasting guidance value, do not update either document.
