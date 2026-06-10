---
id: TASK-133
title: Disable backlog checkActiveBranches by default in ralph-init skill
status: In Progress
assignee: []
created_date: '2026-06-10 04:44'
updated_date: '2026-06-10 04:59'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

TASK-16 disabled `remoteOperations`, which removed the SSH-passphrase prompts on `backlog` CLI calls. But there is a second backlog setting that produces a similar pre-CLI hang in environments without (or with restricted) remote access: `checkActiveBranches`. With it on, `backlog task <N> --plain` and similar read-only commands stall during their active-branch enumeration step, which can need network or local-git operations that are themselves slow / blocked.

Concrete incident (in source repo, 2026-06-09 → 2026-06-10): a `/ralph-run` instance hung during bootstrap before iteration 1 actually started. The log was frozen on `Config: on-error: stop`. Killing the process tree, wiping state files, and re-running did not help. Root cause was the backlog CLI itself stalling on its background active-branch check. Fix that unblocked Ralph:

```bash
backlog config set remoteOperations false      # already done by ralph-init via TASK-16
backlog config set checkActiveBranches false   # missing in template — this task
```

After both flags off, Ralph started iteration 1 within seconds and completed TASK-20 in 11m 22s end-to-end.

Generalize: any ralph-init-bootstrapped project that ends up offline, in a devcontainer with limited git access, or just has a misbehaving remote will hit the same hang. Adding the second flag to the template makes ralph-init projects robust by default, same way TASK-16 did for the first.

## Scope

In scope:
- Edit `skills/ralph-init/SKILL.md` section 3.5: add `backlog config set checkActiveBranches false` immediately after the existing `backlog config set remoteOperations false` line.
- Update the inline comment chain so both `false` lines have short rationales side by side.

Out of scope:
- Changing existing per-project backlog configs (those are user-controlled artifacts).
- Touching the `backlog init` invocation itself or other unrelated config flags.
- Re-running ralph-init in any existing project.

## Files

- `skills/ralph-init/SKILL.md` (exists) — section 3.5 lines 119–124 currently contain only `remoteOperations false`. Add the second flag here.

## Source

Source: /Users/paul/Private/Alfa/Projects/standard/stacks@e8b920f384f8
Related prior task in destination: TASK-16 (same intent, did the first flag).

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. `skills/ralph-init/SKILL.md` still exists in this repo and section 3.5 still contains the `remoteOperations false` line (TASK-16's output).
2. Each AC below is objectively pass/fail (`grep` against the SKILL.md content).
3. No dependency on TASK-16 status beyond what is already present in the file — TASK-16 is already Done.
4. Out-of-scope items are not accidentally pulled in (no edits to existing `backlog/config.yml`, no `backlog init` flag changes, no other config keys).

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-init/SKILL.md section 3.5 contains 'backlog config set checkActiveBranches false' immediately after the existing 'backlog config set remoteOperations false' line
- [x] #2 Each of the two config-set lines has a short inline comment explaining why (remoteOperations: avoids SSH passphrase prompts; checkActiveBranches: avoids backlog CLI stalls in offline / restricted-git environments)
- [x] #3 Order is remoteOperations first, then checkActiveBranches, both BEFORE any other setup commands following 'backlog init'
- [x] #4 grep -c 'backlog config set' skills/ralph-init/SKILL.md returns at least 2
<!-- AC:END -->



## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Edit skills/ralph-init/SKILL.md section 3.5 to add 'backlog config set checkActiveBranches false' line immediately after the existing remoteOperations line, with parallel inline comments on both lines (remoteOperations: SSH passphrase prompts; checkActiveBranches: backlog CLI stalls in offline/restricted-git envs). Verify with grep -c 'backlog config set' == 2. No mirror to live CLAUDE.md needed — only the templates/root/CLAUDE.md file is R11-parity tracked, SKILL.md is not.
<!-- SECTION:NOTES:END -->
