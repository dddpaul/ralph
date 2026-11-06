---
id: TASK-316
title: Guard opted-in autonomous runs against creating tasks
status: In Progress
assignee: []
created_date: '2026-11-04T14:54:00Z'
updated_date: '2026-11-06T17:56:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies:
  - TASK-296
  - TASK-310
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Stop autonomous runs in opted-in projects from creating tasks; follow-ups go into the task's notes instead. Owner decision: the container cannot publish an ID.

A plugin guard refuses backlog task create, shared-backlog create and the ralph-handoff skill when RALPH_AUTONOMOUS=1 and ralph.sharedBacklog is true. It is exempt from the marker gate, and documented as best effort.

Reference: PRD design/plugin-delivered-project-files-prd.md, US-022 and FR-4.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The orchestrator sets RALPH_AUTONOMOUS=1 for every run, including inside the devcontainer
- [x] #2 A new plugin guard wired in hooks.json refuses backlog task create (also after a cd into another repo), shared-backlog.sh create and the ralph:ralph-handoff skill when RALPH_AUTONOMOUS=1 and ralph.sharedBacklog is true, exiting 2 with a record-it-in-notes message
- [x] #3 The guard is exempt from the marker gate and localGuards and keys only on RALPH_AUTONOMOUS and ralph.sharedBacklog
- [x] #4 Docs and the preflight describe the guard as best effort, not an absolute boundary
- [x] #5 The template CLAUDE.md Autonomous Mode text tells the agent to record follow-ups in its notes in opted-in projects
- [x] #6 Tests show the guard refuses in a simulated autonomous run, including with pluginHooks false or absent and the marker removed, and allows the same commands interactively and in clones that do not enforce
- [x] #7 ruff, pytest and bats pass, and bash -n plus the bash 3.2 static guard pass on every changed shell file
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: orchestrator sets RALPH_AUTONOMOUS=1 in every tool subprocess env and forwards it via devcontainer exec --remote-env; new plugins/ralph/hooks/autonomous-create-guard.sh wired directly in hooks.json (Bash|Skill, no run.sh) keyed on RALPH_AUTONOMOUS and the session clone's git config ralph.sharedBacklog; exclude it from managed-file-drift's *-guard.sh copy expectation; preflight/README/SKILL/CLAUDE.md text; tests.

Commit: `88f3db5` - task-316: refuse task creation in autonomous runs of shared-backlog clones

AC #1: host — every tool subprocess gets RALPH_AUTONOMOUS=1 via Popen env (test_child_runs_with_ralph_autonomous_set); devcontainer — argv carries --remote-env RALPH_AUTONOMOUS=1 (argv tests), and `npx -y @devcontainers/cli exec --help` run here lists '--remote-env  Remote environment variables of the format name=value'. No docker in this environment, so the in-container run is deferred to a host: `devcontainer exec --workspace-folder . --remote-env RALPH_AUTONOMOUS=1 sh -c 'printf %s "$RALPH_AUTONOMOUS"'` must print 1.
Review fixes: check=False on the four subprocess.run calls in test_plugin_hooks.py (ruff PLW1510 in a changed file); the guard also matches sh/bash/zsh -c wrappers.
<!-- SECTION:NOTES:END -->
