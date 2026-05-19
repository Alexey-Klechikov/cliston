---
description: "Use when updating AGENTS.md, README.md, or recording durable repository knowledge. Defines what belongs in AGENTS.md versus README.md so documentation updates stay consistent."
applyTo:
  - "AGENTS.md"
  - "README.md"
---
# Documentation Scope

- Put contributor-facing guidance in `AGENTS.md`: fast start, where to look first, codebase conventions, testing notes, validation habits, runtime gotchas, and reusable pitfalls discovered while editing the repo.
- Put service-facing documentation in `README.md`: service purpose, supported behavior, business rules, architecture, external dependencies, setup, and externally useful operational context.
- When one change matters to both audiences, update both files but phrase them differently.
- In `AGENTS.md`, describe what a contributor should remember while changing or testing the code.
- In `README.md`, describe what the service does, how it is structured, or what a reader needs to run or understand it.
- Avoid copying implementation-only debugging notes into `README.md`.
- Avoid putting product or architecture overview material into `AGENTS.md` unless it directly changes how contributors should work in this repository.
