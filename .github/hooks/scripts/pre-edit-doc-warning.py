#!/usr/bin/env python3

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

EDIT_TOOL_NAMES = {
    "apply_patch",
    "create_file",
    "replace_string_in_file",
    "editFiles",
    "createFile",
    "vscode_renameSymbol",
}

DOC_SIGNAL_PATTERN = re.compile(
    r"\b(refactor|rename|move|middleware|hook|instruction|workflow|convention|pitfall|architecture|setup|"
    r"endpoint|environment variable|service structure|validation|logging|context|agent|playwright|"
    r"vectorstore|embedder|rag|task state|browser automation|tool call)\b",
    re.IGNORECASE,
)

DOC_TARGET_MARKERS = (
    "cliston/",
    ".github/",
    "Dockerfile",
    "docker-compose.yml",
    "pyproject.toml",
    "pyrightconfig.json",
    ".pre-commit-config.yaml",
    "example_requests.py",
)


def _read_payload() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def _tool_targets_doc_relevant_path(tool_input: Any) -> bool:
    serialized = json.dumps(tool_input, ensure_ascii=True)
    return any(marker in serialized for marker in DOC_TARGET_MARKERS)


def _transcript_has_doc_signal(transcript_path: str | None) -> bool:
    if not transcript_path:
        return False

    path = Path(transcript_path)
    if not path.exists():
        return False

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False

    return bool(DOC_SIGNAL_PATTERN.search(text[-50000:]))


def _docs_already_changed() -> bool:
    try:
        status_output = os.popen("git status --porcelain --untracked-files=all 2>/dev/null").read()
    except OSError:
        return False

    for line in status_output.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path in {"AGENTS.md", "README.md"}:
            return True
    return False


def main() -> int:
    payload = _read_payload()
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input", {})

    output: dict[str, Any] = {
        "continue": True,
    }

    if tool_name not in EDIT_TOOL_NAMES:
        print(json.dumps(output))
        return 0

    if not _tool_targets_doc_relevant_path(tool_input):
        print(json.dumps(output))
        return 0

    if _docs_already_changed():
        print(json.dumps(output))
        return 0

    if not _transcript_has_doc_signal(payload.get("transcript_path")):
        print(json.dumps(output))
        return 0

    output["systemMessage"] = (
        "This edit targets cliston/, .github/, or repo runtime files and the active task looks likely "
        "to change durable repo knowledge. "
        "If you confirm a reusable pitfall, workflow, convention, or externally useful behavior, update "
        "AGENTS.md and/or README.md before finishing."
    )
    output["hookSpecificOutput"] = {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "additionalContext": (
            "Use AGENTS.md for contributor workflow, testing notes, conventions, and pitfalls. "
            "Use README.md for durable service behavior, architecture, setup, and externally useful context."
        ),
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
