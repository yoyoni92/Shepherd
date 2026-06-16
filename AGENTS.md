# Shepherd - Repo Rules

## Pre-commit: documentation must be in sync (REQUIRED)

Before **every** commit, the agent MUST verify that the related Markdown docs reflect the staged
changes, and update them in the **same commit**. Do not commit code/doc drift.

Check and update, as relevant to what changed:

- **`plans/` design docs** (`../plans/*.md`) - if a decision, schema, contract, or interface changed.
- **`plans/implementation/*.md`** - if a task's scope, test list, or Definition of Done changed; tick
  off completed tasks.
- **Service `README.md`** and root **`README.md`** - if setup, commands, or layout changed.
- **`.env.example`** - if any new config/secret/env var was introduced.
- **`AGENTS.md` / `CLAUDE.md`** (same file via symlink) - if a repo rule changed.
- **`plans/README.md` "open questions"** - mark resolved ones; add new ones surfaced during build.

Procedure each commit:
1. `git diff --staged --name-only` - list what changed.
2. For each area above, confirm the matching docs are updated (or explicitly note "no doc impact").
3. Stage the doc updates **with** the code. Only then commit.

If unsure whether a doc needs updating, update it - stale docs are worse than verbose ones.

## Agent skills

### Issue tracker

Issues and PRDs live as markdown files under `.scratch/<feature>/` in this repo. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical triage roles, each using its default string (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
