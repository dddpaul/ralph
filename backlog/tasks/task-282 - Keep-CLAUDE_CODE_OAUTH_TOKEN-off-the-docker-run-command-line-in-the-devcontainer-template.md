---
id: TASK-282
title: >-
  Keep CLAUDE_CODE_OAUTH_TOKEN off the docker run command line in the
  devcontainer template
status: To Do
assignee: []
created_date: '2026-10-29T11:40:00Z'
labels:
  - devcontainer
  - template
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

The devcontainer template forwards the host's long-lived Claude token through `containerEnv` (`"CLAUDE_CODE_OAUTH_TOKEN": "${localEnv:CLAUDE_CODE_OAUTH_TOKEN}"`, TASK-114). The devcontainer CLI turns a containerEnv entry into `docker run ... -e CLAUDE_CODE_OAUTH_TOKEN=<value>`, and that `docker run --sig-proxy=false -a STDOUT -a STDERR ...` process stays alive, reparented to init, for as long as the container runs. So the token value sits in the host's process list (`ps -eo args`) for the container's whole lifetime, readable by any process that can list processes on the host.

Found on the agentbox on 2026-10-29 (mycloud TASK-93): `ps -eo args`, grepped with the token read from a file via `-f`, matched two such `docker run` processes, one for a project's long-running Ralph devcontainer and one for a test container started from this repo's `.devcontainer`. No claude or happy process had the token on argv; only the `docker run` lines did.

Candidate fix: drop the containerEnv entry and pass only the variable's name, `"runArgs": [..., "-e", "CLAUDE_CODE_OAUTH_TOKEN"]`. Given `-e NAME` without `=value`, docker takes the value from its own environment, which it inherits from the devcontainer CLI (and so from the shell or the orchestrator), and the value never lands on argv. An unset variable is simply not set in the container, which keeps TASK-114's graceful degradation. Verify it by invoking the tools (AC3 to AC5): a static grep cannot see whether the value actually arrives.

## Scope

In scope:
- This repo's live `.devcontainer/devcontainer.json` and the ralph-init template, kept in parity.
- A test pinning the name-only forward.
- The ralph-init SKILL.md passage that documents the token forward (the containerEnv / `${localEnv:...}` text around the macOS setup steps).

Out of scope:
- Other containerEnv entries.
- `docker inspect` still showing the value in Config.Env to anyone with docker access; that is how docker stores container env, not argv.
- Downstream projects: they pick the change up through the ralph-init upgrade.
- The agentbox SessionStart hook that hands the token to Bash tool commands (mycloud TASK-93), which is done.

## Files

- `.devcontainer/devcontainer.json` (exists): remove the containerEnv token entry, add `"-e", "CLAUDE_CODE_OAUTH_TOKEN"` to runArgs.
- `plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json` (exists): the same change, in parity.
- `plugins/ralph/skills/ralph-init/SKILL.md` (exists): describe the name-only forward and why.
- `tests/unit/template-parity.bats` (exists): must keep passing.
- `tests/python/test_devcontainer_oauth_token_forward.py` (to-create): pin the template's runArgs and the absence of the containerEnv entry, unless an existing devcontainer test is the better home.

## Source

Source: /Users/paul/Private/Projects/mycloud@9e6b9c029ca2
Source task (read-only context, do NOT modify): /Users/paul/Private/Projects/mycloud/backlog/tasks/task-93 - Restore-CLAUDE_CODE_OAUTH_TOKEN-in-Bash-tool-commands-on-the-agentbox-with-a-SessionStart-hook.md

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
- [ ] #1 Neither .devcontainer/devcontainer.json nor plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json has a CLAUDE_CODE_OAUTH_TOKEN key in containerEnv, and both list "-e", "CLAUDE_CODE_OAUTH_TOKEN" (the name only, no =) in runArgs
- [ ] #2 A test pins the template's name-only forward and the absent containerEnv entry, and uv run pytest and the template-parity bats suite pass
- [ ] #3 With CLAUDE_CODE_OAUTH_TOKEN exported in the host shell, a freshly created container from the changed devcontainer.json (devcontainer up) reports a non-zero token length via devcontainer exec sh -c 'printf %s ${#CLAUDE_CODE_OAUTH_TOKEN}', and ps -eo args on the host, grepped with the token read via -f from a umask 077 mktemp file, counts 0; both results are recorded in the task notes
- [ ] #4 In that container, devcontainer exec claude -p 'Reply with the single word OK' answers rather than reporting Not logged in
- [ ] #5 With CLAUDE_CODE_OAUTH_TOKEN unset in the host shell, devcontainer up of a fresh container still succeeds and the in-container token length prints 0
- [ ] #6 plugins/ralph/skills/ralph-init/SKILL.md describes the token forward as the name-only runArgs entry and says why: a containerEnv value becomes docker run -e NAME=value, visible in the host's ps for the container's lifetime
<!-- AC:END -->
