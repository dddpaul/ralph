---
id: TASK-289
title: >-
  Warn in devcontainer preflight about user-global hooks that point at host-only
  paths
status: To Do
assignee: []
created_date: '2026-11-03T05:45:00Z'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

The devcontainer now shares the host `~/.claude` (second bind at the host path, `CLAUDE_CONFIG_DIR` pointing there), so Claude Code inside the container loads the user's global `~/.claude/settings.json` — including its `hooks`. Hooks whose command lives outside `~/.claude` are not reachable in the container: `$HOME` is `/home/node` there and only `~/.claude` is mounted. Seen in a consumer project (equation/core) after the 0.14.7 upgrade: every Ralph session ends with `SessionEnd hook ["$HOME/.config/claude-trim/claude-trim" --hook] failed: /bin/sh: 1: /home/node/.config/claude-trim/claude-trim: not found`, and an agterm status hook (`/Users/<user>/.config/agterm/agent-status/agterm-claude-status.sh`) fails the same way on every PostToolUse/Stop/UserPromptSubmit.

Making such hooks reachable is the wrong fix. claude-trim decides a transcript is ownerless when `ps -p <pid>` cannot find the Claude pid recorded in `~/.claude/sessions/*.json`; inside the container's pid namespace no host process is visible, so its SessionStart sweep would treat live host sessions as ownerless and trim their transcripts. The "not found" failure is therefore protective, just noisy and unexplained. The user chose: Ralph warns about such hooks in preflight and documents a contract (`DEVCONTAINER=true`, already set by `Dockerfile.base`) that hook authors use to skip themselves in the container. Ralph does not touch the hooks.

## Scope

In scope:
- `ralph-run` preflight, only when `devcontainer=true`: read the user settings file (`${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json`), walk every `hooks.<Event>[].hooks[].command`, and print one stderr line per command whose executable is a path outside the user Claude config dir, e.g. `WARNING: user hook not reachable in the devcontainer — SessionEnd: "$HOME/.config/claude-trim/claude-trim" --hook (guard it with DEVCONTAINER, see ralph-init)`. Path forms to classify: absolute paths, `$HOME/...` / `${HOME}/...` / `~/...` (quoted or not). Bare command names (`jq`, `bash`) and paths under the config dir (`$HOME/.claude/...`, `/Users/<user>/.claude/...`) are not warned about. Never changes the exit code; the `OK RALPH_PATH=...` line still prints. Same shape as the existing `_check_managed_drift` warning.
- `ralph-run` SKILL.md Step 3: document the new warning (relay once, never abort), next to the managed-file warning paragraph.
- `ralph-init` SKILL.md devcontainer notes (near the "Second bind of the user ~/.claude" note): user-global hooks run inside the container; `$HOME` is `/home/node`; host-only paths fail with "not found"; guard them with `[ "${DEVCONTAINER:-}" = true ] && exit 0`; claude-trim as the worked example of why reachability would be unsafe (pid namespace).
- pytest coverage for the classifier and the preflight output.

Out of scope:
- mounting `~/.config` or any host-only tool into the container;
- stripping, filtering or rewriting user hooks or `~/.claude/settings.json`;
- changing claude-trim, agterm or any user tool;
- `devcontainer=false` runs (no check there).

## Files

- `plugins/ralph/skills/ralph-run/scripts/ralph/preflight.py` (exists) — new check after `_check_managed_drift`, devcontainer=true only
- `plugins/ralph/skills/ralph-run/SKILL.md` (exists) — Step 3 warning paragraph
- `plugins/ralph/skills/ralph-init/SKILL.md` (exists) — devcontainer notes, user-hook contract
- `tests/python/test_preflight_host_only_hooks.py` (to-create) — fixture settings.json with the four cases below

Fixture cases: `"$HOME/.config/claude-trim/claude-trim" --hook` (warn), `'/Users/x/.config/agterm/agent-status/agterm-claude-status.sh' active --blink` (warn), `/Users/x/.claude/hooks/peon-ping/peon.sh` with CLAUDE_CONFIG_DIR=/Users/x/.claude (no warn), `jq -r .x` (no warn).

## Source

Source: /Users/paul/Private/Alfa/Projects/equation/core@2a69c66359bb
Source context (read-only, do NOT modify): /Users/paul/.config/claude-trim/README.md (liveness check: "A transcript is owned when an entry in ~/.claude/sessions/*.json names its session id with a pid that is alive…").

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, build command, or visible behavior — not "works correctly").
3. All dependencies in the task's frontmatter are status=Done.
4. Out-of-scope items are not accidentally pulled in by ambiguous AC.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 With devcontainer=true and a user settings.json holding the claude-trim and agterm hook commands from the fixture, preflight prints exactly one 'WARNING: user hook not reachable in the devcontainer' stderr line per such command (event name and command included) and still exits 0 with the OK RALPH_PATH line
- [ ] #2 Hook commands under the user Claude config dir ($HOME/.claude/..., /Users/<user>/.claude/...) and bare command names (jq) produce no warning
- [ ] #3 With devcontainer=false, or when settings.json is missing, unparsable or has no hooks key, preflight prints no such warning and its exit code is unchanged
- [ ] #4 plugins/ralph/skills/ralph-run/SKILL.md Step 3 documents the 'user hook not reachable in the devcontainer' warning as relay-once, never-abort
- [ ] #5 plugins/ralph/skills/ralph-init/SKILL.md devcontainer notes document the user-hook contract: hooks from the shared ~/.claude run in the container, $HOME is /home/node, guard with [ "${DEVCONTAINER:-}" = true ] && exit 0, and claude-trim as the example why making host-only hooks reachable is unsafe (pid namespace)
- [ ] #6 tests/python/test_preflight_host_only_hooks.py covers the four fixture cases plus the devcontainer=false and missing-settings cases; uv run pytest and uv run ruff check . pass
<!-- AC:END -->
