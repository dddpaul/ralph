---
id: TASK-289
title: >-
  Warn in devcontainer preflight about user-global hooks that point at host-only
  paths
status: Done
assignee: []
created_date: '2026-11-03T05:45:00Z'
updated_date: '2026-11-03T17:19:00Z'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

The devcontainer now shares the host `~/.claude` (second bind at the host path, `CLAUDE_CONFIG_DIR` pointing there), so Claude Code inside the container loads the user's global `~/.claude/settings.json` — including its `hooks`. Hooks whose command lives outside `~/.claude` are not reachable in the container: `$HOME` is `/home/node` there and only `~/.claude` is mounted. Seen in a consumer project (equation/core) after the 0.14.7 upgrade: every Ralph session ends with `SessionEnd hook ["$HOME/.config/claude-trim/claude-trim" --hook] failed: /bin/sh: 1: /home/node/.config/claude-trim/claude-trim: not found`, and an agterm status hook (`/Users/<user>/.config/agterm/agent-status/agterm-claude-status.sh`) fails the same way on every PostToolUse/Stop/UserPromptSubmit.

Making such hooks reachable is the wrong fix. claude-trim decides a transcript is ownerless when `ps -p <pid>` cannot find the Claude pid recorded in `~/.claude/sessions/*.json`; inside the container's pid namespace no host process is visible, so its SessionStart sweep would treat live host sessions as ownerless and trim their transcripts. The "not found" failure is therefore protective, just noisy and unexplained. The user chose: Ralph warns about such hooks in preflight and documents a contract (`DEVCONTAINER=true`, already set by `Dockerfile.base`) that users apply to skip such hooks in the container. Ralph does not touch the hooks.

The guard goes in the hook's `command` in `settings.json`, not inside the script: the script is exactly what the container cannot reach, so a guard inside it never runs.

```bash
[ "${DEVCONTAINER:-}" = true ] || "$HOME/.config/claude-trim/claude-trim" --hook
```

## Scope

In scope:
- `ralph-run` preflight, only when `devcontainer=true`: read the user settings file (`${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json`), walk every `hooks.<Event>[].hooks[].command`, and print one stderr line per command whose executable is a path outside the user Claude config dir, e.g. `WARNING: user hook not reachable in the devcontainer — SessionEnd: "$HOME/.config/claude-trim/claude-trim" --hook (guard the hook command with DEVCONTAINER, see ralph-init)`. Path forms to classify: absolute paths, `$HOME/...` / `${HOME}/...` / `~/...` (quoted or not). Bare command names (`jq`, `bash`) and paths under the config dir (`$HOME/.claude/...`, `/Users/<user>/.claude/...`) are not warned about, and neither is a command guarded as above (it starts with `[`, a bare name). Never changes the exit code; the `OK RALPH_PATH=...` line still prints. Same shape as the existing `_check_managed_drift` warning.
- `ralph-run` SKILL.md Step 3: document the new warning (relay once, never abort), next to the managed-file warning paragraph.
- `ralph-init` SKILL.md devcontainer notes (near the "Second bind of the user ~/.claude" note): user-global hooks run inside the container; `$HOME` is `/home/node`; host-only paths fail with "not found"; guard the hook command in settings.json with `[ "${DEVCONTAINER:-}" = true ] || <command>`, not the script, which the container cannot reach; claude-trim as the worked example of why reachability would be unsafe (pid namespace).
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
- `tests/python/test_preflight_host_only_hooks.py` (to-create) — fixture settings.json with the five cases below

Fixture cases: `"$HOME/.config/claude-trim/claude-trim" --hook` (warn), `'/Users/x/.config/agterm/agent-status/agterm-claude-status.sh' active --blink` (warn), `/Users/x/.claude/hooks/peon-ping/peon.sh` with CLAUDE_CONFIG_DIR=/Users/x/.claude (no warn), `jq -r .x` (no warn), `[ "${DEVCONTAINER:-}" = true ] || "$HOME/.config/claude-trim/claude-trim" --hook` (no warn).

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
- [x] #1 With devcontainer=true and a user settings.json holding the claude-trim and agterm hook commands from the fixture, preflight prints exactly one 'WARNING: user hook not reachable in the devcontainer' stderr line per such command (event name and command included) and still exits 0 with the OK RALPH_PATH line
- [x] #2 Hook commands under the user Claude config dir ($HOME/.claude/..., /Users/<user>/.claude/...), bare command names (jq) and a command prefixed with the DEVCONTAINER guard produce no warning
- [x] #3 With devcontainer=false, or when settings.json is missing, unparsable or has no hooks key, preflight prints no such warning and its exit code is unchanged
- [x] #4 plugins/ralph/skills/ralph-run/SKILL.md Step 3 documents the 'user hook not reachable in the devcontainer' warning as relay-once, never-abort
- [x] #5 plugins/ralph/skills/ralph-init/SKILL.md devcontainer notes document the user-hook contract: hooks from the shared ~/.claude run in the container, $HOME is /home/node, guard the hook command in settings.json with [ "${DEVCONTAINER:-}" = true ] || <command> (not inside the script, which the container cannot reach), and claude-trim as the example why making host-only hooks reachable is unsafe (pid namespace)
- [x] #6 tests/python/test_preflight_host_only_hooks.py covers the five fixture cases plus the devcontainer=false and missing-settings cases; uv run pytest and uv run ruff check . pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Handoff gate (destination): yellow, clarified with the user. Y1 - the DEVCONTAINER guard goes in the hook's command in settings.json ([ "${DEVCONTAINER:-}" = true ] || <command>), not inside the script: the scripts this warns about are the ones the container cannot reach, so a guard inside them never runs. Description, warning hint, AC #2, AC #5 and a fifth fixture case (guarded command, no warning) changed accordingly. Y2 - on the owner's Mac the check prints 7 lines per devcontainer launch until the hooks are guarded: claude-trim for SessionStart and SessionEnd, the agterm status hook for 5 events.

Plan: add _check_user_hooks (devcontainer=true only) after _check_managed_drift in preflight.py: shlex the first word of each hooks.<Event>[].hooks[].command, expand $HOME/${HOME}/~ prefixes, warn when the path is absolute and outside CLAUDE_CONFIG_DIR and $HOME/.claude; document in ralph-run Step 3 and ralph-init devcontainer notes; pytest in tests/python/test_preflight_host_only_hooks.py.

Commit: `9f65c99` - task-289: warn in devcontainer preflight about user hooks that run from host-only paths

Implemented _check_user_hooks (preflight check 8, devcontainer=true only, report-only). It reads ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json and shlex-splits each hook command, classifying the first word. Absolute paths and $HOME/${HOME}/~ paths outside the config dir and $HOME/.claude produce warnings. Bare names, the [ DEVCONTAINER guard, and missing, unparsable or hookless settings produce none. The owner's real settings yield 7 warnings (claude-trim x2, agterm x5), matching Y2. Documented in ralph-run Step 3 and ralph-init devcontainer notes. Also fixed the .venv note's 'note directly above' pointer, which the insertion would have made wrong. Tests: tests/python/test_preflight_host_only_hooks.py (15). Gates: pytest 936 passed/3 skipped, ruff clean, pyright 0 errors. Review: ralph:task-reviewer APPROVED, 1 minor not taken (unset HOME, unrealistic for a host preflight).

Commit: `bd14525` - task-289: bump plugin version to 0.14.11 (patch)

macOS host verification (after merge, master 0.14.11): _check_user_hooks('true', False) against the owner's ~/.claude/settings.json prints exactly 7 'WARNING: user hook not reachable in the devcontainer' lines: the agterm status hook for Notification, PermissionRequest, PostToolUse, Stop and UserPromptSubmit, and claude-trim for SessionStart and SessionEnd. It prints none for the peon-ping and notify hooks under ~/.claude or for the CLAUDE_ENV_FILE one-liner; with devcontainer=false preflight prints none. The check was run directly because the full preflight.sh stops at 'ERROR: No To Do tasks in backlog' before reaching it when the backlog has no To Do tasks.
<!-- SECTION:NOTES:END -->
