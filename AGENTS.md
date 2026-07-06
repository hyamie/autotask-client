# AGENTS.md

> Codex agent guide for **autotask-client**. Global/universal agent rules live in `~/.codex/AGENTS.md`;
> this file holds only what is specific to this repo.

## Project Context

autotask-client is an async Python client library for the Autotask PSA REST API. It handles auth and
zone discovery, rate limiting, pagination, Pydantic entity models, a Click-based CLI, and a FastMCP
server for agent access. Python 3.12+, managed with uv (see `uv.lock`); builds with hatchling.

## Verify

Run after any change (documentation included):

```
pytest && ruff check src/ tests/ && mypy src/
```

## Git flow

- Work on `main`. Direct commits to `main` are fine for this repo.
- Conventional-commit subjects: `type(scope): summary`.
- Stage only the files you changed. Never `git add .`.

## Cross-agent files (read before working)

This repo is worked by both Claude Code and Codex (Desktop app / CLI). Keep the two from drifting or
leaving the tree messy:

- **`CLAUDE.md` is READ-ONLY to Codex. Under no circumstances may Codex create, edit, delete, move, or
  reformat `CLAUDE.md`, or anything under `.claude/`.** It is Claude Code's context and workflow
  surface. Read it for project context if useful, but never write to it. If something in it looks
  wrong or stale, report it. Do not change it.
- **`AGENTS.md` (this file)** is the shared cross-agent contract and the only durable-instruction file
  Codex edits.
- Universal agent rules (no-mess git hygiene, work modes, secrets, commit format) live in the global
  `~/.codex/AGENTS.md` and apply here. This file holds only repo-specific facts.
