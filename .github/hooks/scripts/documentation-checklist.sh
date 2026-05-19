#!/bin/sh

cat >/dev/null

status_output=$(git status --porcelain --untracked-files=all 2>/dev/null || true)

if [ -z "$status_output" ]; then
  printf '%s\n' '{"continue":true}'
  exit 0
fi

printf '%s\n' '{"continue":true,"systemMessage":"Documentation checklist: 1. Did this change reveal a reusable workflow, testing note, or pitfall for AGENTS.md? 2. Did it change durable service behavior, architecture, setup, or externally useful expectations for README.md? 3. If neither applies, leave the docs unchanged."}'
