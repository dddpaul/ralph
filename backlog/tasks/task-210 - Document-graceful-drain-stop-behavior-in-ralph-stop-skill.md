---
id: TASK-210
title: Document graceful-drain stop behavior in ralph-stop skill
status: Done
assignee: []
created_date: '2026-07-22 19:10'
updated_date: '2026-07-23 09:14'
labels: []
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ralph-stop's stop signal reaches only the host-side orchestrator (ralph.sh — the PID in the status file), NOT the AI agent (claude -p / opencode) running the current iteration. For --devcontainer runs that agent is a Docker-isolated process the host's `pkill -P <pid>` / `kill` cannot see. This is intentional and produces a graceful drain, but it is non-obvious — someone could wrongly "fix" it into a force-kill, which would corrupt in-flight work.

Observed live: a "stop after TASK-202" let the in-container agent finish TASK-203 gracefully and merge it cleanly, then the loop halted because no orchestrator remained to spawn TASK-204. No dirty state, no git reset needed. Document this so the behavior is understood and preserved.

Deliverable: insert the following section into plugins/ralph/skills/ralph-stop/SKILL.md, right after the intro line "Gracefully stop a running Ralph autonomous agent." and its horizontal rule, before "## Step 1". Use this exact content:

## Behavior: graceful drain, not mid-iteration kill

`ralph-stop` signals the **host-side orchestrator** (`ralph.sh` — the PID in the status file). It does NOT reach the AI agent (`claude -p` / `opencode`) running the current iteration: for `--devcontainer` runs that agent is a Docker-isolated process the host's `pkill -P <pid>` / `kill` cannot see.

This is intentional. The effect is a **graceful drain**:

- SIGTERM to the orchestrator stops it from spawning the *next* iteration.
- The in-flight iteration's agent keeps running to completion and merges its task cleanly.
- The loop then halts because no orchestrator remains to start the following task.

So "stop" lands on a **clean task boundary**: the current task finishes and merges (no half-written diff), then Ralph stops. Net semantics: *"stop after task N"* drains to *"after N plus whatever task is already in flight."*

Do NOT "fix" this by force-killing the in-container agent (e.g. `devcontainer exec ... pkill claude`). Killing `claude -p` mid-iteration leaves a partial, uncommitted diff on the task branch that needs `git reset` + manual cleanup — the opposite of a graceful stop.

Note: ralph-stop is a plugin skill, not a bootstrap-seeded template, so there is NO R11 template-parity pair to also edit — single file change. The installed plugin-cache copy updates on next plugin reinstall; only the repo source is edited here.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 plugins/ralph/skills/ralph-stop/SKILL.md contains a "## Behavior: graceful drain, not mid-iteration kill" section inserted between the intro and "## Step 1"
- [x] #2 The section states the stop reaches only the host orchestrator, not the in-container claude -p agent, and that this is intentional (graceful drain to a clean task boundary)
- [x] #3 The section explicitly warns against force-killing the in-container agent and explains it would leave a dirty diff needing git reset
- [x] #4 No other Step sections are reworded or reordered
- [x] #5 grep confirms ralph-stop is not under plugins/ralph/skills/ralph-init/templates/, so no R11 template pair edit is required
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Single-file doc edit. Insert the '## Behavior: graceful drain, not mid-iteration kill' section into plugins/ralph/skills/ralph-stop/SKILL.md between the intro line 'Gracefully stop a running Ralph autonomous agent.' + its '---' rule (line 10) and '## Step 1' (line 12), using the exact content from the task deliverable. No Step sections touched. Verified AC#5: no ralph-stop under ralph-init/templates/ (find returned empty). Lint: uv run ruff check .; no .py changed. No R11 pair.

Commit: `5733eaa` - task-210: document graceful-drain stop behavior in ralph-stop skill

Done: Inserted '## Behavior: graceful drain, not mid-iteration kill' section into plugins/ralph/skills/ralph-stop/SKILL.md (18 insertions, 0 deletions) between the intro and Step 1, byte-for-byte per the deliverable. All 5 AC met. Steps 1-7 unchanged (insertion-only diff). AC#5 verified: no ralph-stop under ralph-init/templates/ (git ls-files empty) — no R11 pair. Lint clean (uv run ruff check .), 317 pytest tests pass, no .py changed. task-reviewer agent: APPROVED. Note: commit-prefix-guard.sh needs a single-line -m subject (its sed can't parse a multi-line -m body → empty msg → false block).
<!-- SECTION:NOTES:END -->
