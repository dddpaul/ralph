---
id: doc-6
title: Plugin-Delivered Project Files Overview
type: other
created_date: '2026-11-04T14:55:00Z'
updated_date: '2026-11-04T14:55:00Z'
---
# Plugin-Delivered Project Files Overview

Reference sheet for the feature with the label feature:plugin-delivered-project-files. The full design is in design/plugin-delivered-project-files-prd.md and in the brainstorm next to it.

## Goal

A plugin update should reach every migrated Ralph project on a host, with no upgrade run per project or per clone.

Opted-in projects also get a shared-backlog protocol. Under it, the push to origin decides which task IDs and claims are real, so two clones never collide on an ID and never start the same task.

## Tech stack

- Bash 3.2-compatible shell: the shims, hooks and shared-backlog script.
- Python: the orchestrator and preflight.
- Claude Code plugin hooks (hooks/hooks.json).
- The git hooks.
- jq, for reading Claude Code's plugin registry.

## Architecture

**What each project and clone carries:**
- A tracked marker, .claude/ralph.json, with pluginHooks, localGuards, sharedBacklog and checks. It declares intent.
- Trusted per-clone switches in git config: ralph.pluginHooks and ralph.sharedBacklog. They enforce.
- Fixed shims in each clone. They find the installed plugin through installed_plugins.json, matching project scope by ralph.projectPath.

**What the plugin carries:**
- The Claude guards, behind a marker-gated dispatcher.
- The git hook bodies.
- A user-settings fragment.
- The shared-backlog script. Its create works in a temporary worktree under a lock, and its integrate merges and never renumbers.

**Release gate:** the shared-backlog protocol stays behind a gate until its last task is done.

## Scope

**In scope:**
- the guards and the git hooks;
- the common allow rules;
- the migration, plus Init and Upgrade;
- the shared-backlog protocol: claim, create, integrate, the pre-push duplicate check, the picker claim lifecycle and the no-create guard;
- the handoff state table;
- R-INFRA-6 provenance;
- release tag validation, for this repo only.

**Out of scope:**
- .devcontainer, CLAUDE.md and brainstorm-rules delivery;
- batch migration;
- Codex support;
- per-host ID ranges;
- automatic renumbering.

## Task dependency graph

**Plugin-delivered files:**

    TASK-295 resolver -> TASK-297 git shim
    TASK-296 guards, TASK-297, TASK-298 settings fragment -> TASK-299 tracked migration
      -> TASK-300 clone migration -> TASK-301 Init/Upgrade -> TASK-302 self-migration + host checks

**Shared backlog:**

    TASK-303 stage-1 import (interactive) -> TASK-304 locks/deadlines -> TASK-305 claim rules
      -> TASK-306 merge-only claim/release -> TASK-307 worktree create -> TASK-308 reconcile/recovery
    TASK-304, TASK-305 -> TASK-309 integrate
    TASK-295, TASK-300, TASK-304 -> TASK-310 shim + enable/disable
    TASK-297, TASK-305, TASK-307, TASK-308, TASK-310 -> TASK-311 pre-push duplicate check
    TASK-309, TASK-311 -> TASK-312 publish lifecycle -> TASK-313 container checks + timeout
    TASK-314 picker assignees (independent)
    TASK-306, TASK-310, TASK-312, TASK-314 -> TASK-315 claim lifecycle
    TASK-296, TASK-310 -> TASK-316 no-create guard
    TASK-308, TASK-310 -> TASK-317 handoff state table
    TASK-309 -> TASK-318 R-INFRA-6 provenance
    TASK-319 release tag validation (independent, this repo only)
    TASK-308, 311, 313, 315, 316, 317 -> TASK-320 release the protocol

## How the tasks run

- **(host) criteria** are checked on the macOS host after the Ralph run, and the task does not count as complete until they are recorded.
- **TASK-303 runs interactively,** because the devcontainer cannot see the source repo.
