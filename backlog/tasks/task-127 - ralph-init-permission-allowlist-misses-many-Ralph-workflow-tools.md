---
id: TASK-127
title: ralph-init permission allowlist misses many Ralph workflow tools
status: To Do
assignee: []
created_date: '2026-05-19 08:34'
updated_date: '2026-05-19 08:46'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
After a fresh `/ralph-init` run, the generated `.claude/settings.local.json` allowlist still leaves Claude Code prompting the user for permission on a long list of tools that are part of the *normal* Ralph daily workflow. Reproduced today in `/Users/paul/Private/Alfa/Projects/enterprise` (init → ralph-prd-like work → /ralph-run with watch=5m).

## What the template ships today

`templates/claude/settings.local.json` allowlist:

```
Bash(backlog --help:*), Bash(backlog status), Bash(backlog task --help:*),
Bash(backlog task create:*), Bash(backlog task edit:*), Bash(backlog task list:*),
Bash(backlog init:*), Bash(backlog doc:*), Bash(backlog overview),
Bash(git add:*), Bash(git commit:*), Bash(git config:*),
Bash(./ralph.sh:*), Bash(nohup ./ralph.sh:*),
Bash(grep:*), Bash(stat:*), Bash(date:*), Bash(echo:*),
Bash(command -v:*), Bash(bash -n:*), Bash(test:*), Bash(npm test:*),
Skill(ralph-run), Skill(ralph-status), Skill(ralph-stop), Skill(brainstorm)
```

Plus Step 3.7b appends six narrow rules (3 abs path + 3 `$HOME`-form) for `preflight.sh`, `wait-heartbeat.sh`, `utc-to-moscow.sh`.

## What is missing — observed in this session

### A. Skills routinely invoked

| Skill | Why it triggers | Frequency |
|---|---|---|
| `Skill(ralph-status-watch)` | Self-scheduled by `ralph-run` via `ScheduleWakeup` every `watch` interval. NOT user-facing — internal to the watch loop. | Every 5 min while Ralph runs. **Highest pain point.** |
| `Skill(ralph-task)` | Ad-hoc task creation / edit-deliberation | Per ad-hoc task |
| `Skill(ralph-init)` | Upgrade flow (`ralph upgrade`) | Per upgrade |
| `Skill(pptx-arch-style)` | Architectural slide work | Per slide task |
| `Skill(example-skills:pptx)` | Same | Same |
| `Skill(fewer-permission-prompts)` | This very investigation | Periodic |

### B. Deferred / built-in tools

None of these are in the template; every invocation prompts:

`ScheduleWakeup` (mandatory for `ralph-status-watch` chain), `TaskCreate`, `TaskUpdate`, `TaskGet`, `TaskList`, `TaskStop`, `TaskOutput`, `ToolSearch`, `mcp__happy__change_title`.

### C. Bash commands used in normal Ralph task flow

| Pattern | Where it appears in the flow |
|---|---|
| `Bash(mkdir:*)`, `Bash(cp:*)`, `Bash(mv:*)`, `Bash(rm:*)`, `Bash(rmdir:*)`, `Bash(chmod:*)`, `Bash(tee:*)` | File ops during implementation, scaffolding, fixing perms on scripts |
| `Bash(git checkout:*)` | Required to create `task-<id>` branches (CLAUDE.md Task Lifecycle step 1→6) |
| `Bash(git merge:*)` | Step 6 of Task Lifecycle — merge task branch back to master |
| `Bash(git mv:*)`, `Bash(git rm:*)`, `Bash(git init:*)` | Legacy migration, removing obsolete files, reinit during ralph-init |
| `Bash(backlog task view:*)` | **Mandatory** self-check in `ralph-task` skill (`backlog task view <id> --plain | grep -A20 Acceptance`) |
| `Bash(backlog task archive:*)` | Archive misaligned tasks (this session: archived TASK-2 before recreating) |
| `Bash(backlog config:*)` | Set/get config like `remoteOperations` (init Step 3.5 already uses this) |
| `Bash(backlog doc view:*)`, `Bash(backlog doc list:*)` | Browsing project docs |
| `Bash(jq:*)` | Used by *this very init skill* (Step 3.7b) and by anything modifying `.claude/settings*.json` |
| `Bash(ps:*)`, `Bash(kill:*)` | Inspect / kill Ralph process |
| `Bash(tail:*)`, `Bash(head:*)`, `Bash(wc:*)` | Log inspection, line counts |

### D. Pattern-syntax pitfall — `:*` does not cover no-arg invocations

The Step 3.7b narrow rules are written as e.g.

`Bash(bash $HOME/.claude/skills/ralph-run/scripts/wait-heartbeat.sh:*)`

Observed behavior in this session: when the matching skill (`ralph-run`) invokes the script **without** any trailing arguments — `bash $HOME/.../wait-heartbeat.sh` — Claude Code still asks for approval. Adding an explicit exact-form rule `Bash(bash $HOME/.../wait-heartbeat.sh)` (no `:*`) resolved it.

The `:*` suffix appears to require at least one trailing token to match. `wait-heartbeat.sh` and `utc-to-moscow.sh` both have legitimate no-arg call sites in the skills.

### E. Skill body uses scripts not in allowlist

The pptx skill family (`example-skills:pptx`) recommends running `python scripts/office/soffice.py` and `pdftoppm`, but the init template does not anticipate these even when the user picks a Documentation project type (0B) which the init flow already configures for pptx generation in the devcontainer.

## Net effect

A user who follows the documented Ralph happy path — `ralph-init` → `/ralph-prd` → `/ralph-backlog` → `/ralph-run watch=5m` — gets prompted **dozens of times** in the first hour:

- Every `/ralph-status-watch` tick → 2-3 prompts (Skill + ScheduleWakeup + sometimes the no-arg `utc-to-moscow.sh`)
- Every internal jq-merge against settings.local.json → 1 prompt
- Every `backlog task view` self-check after `backlog task create` → 1 prompt
- Every file operation during implementation → 1 prompt
- Every `git checkout -b task-<id>` and `git merge` → 1 prompt

The user explicitly flagged this multiple times in the same session as the reason Ralph feels disruptive rather than autonomous.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Split into sibling tasks per user request:
- TASK-128 (HIGH) — Skill + ScheduleWakeup allowlist additions (Section A + B subset)
- TASK-129 (HIGH) — Safe bash wildcard patterns, destructive commands EXCLUDED per user safety constraint (Section C)
- TASK-130 (HIGH) — :* no-arg invocation pitfall: controlled repro + fix or document (Section D)
- TASK-131 (MEDIUM) — pptx helpers for Documentation/Mixed project types (Section E)

This umbrella task can be closed once all four siblings reach Done. Each has --dep task-127.
<!-- SECTION:NOTES:END -->
