---
id: TASK-282
title: >-
  Keep CLAUDE_CODE_OAUTH_TOKEN off the docker run command line in the
  devcontainer template
status: Done
assignee: []
created_date: '2026-10-29T11:40:00Z'
updated_date: '2026-11-03 16:52'
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

Candidate fix: drop the containerEnv entry and pass only the variable's name, as one runArgs element, `"runArgs": [..., "--env=CLAUDE_CODE_OAUTH_TOKEN"]`. Given `--env=NAME` without `=value`, docker takes the value from its own environment, which it inherits from the devcontainer CLI (and so from the shell or the orchestrator), and the value never lands on argv. An unset variable is simply not set in the container, which keeps TASK-114's graceful degradation. Verify it by invoking the tools (AC3 to AC5): a static grep cannot see whether the value actually arrives. AC3 to AC5 need docker and the devcontainer CLI, which the Ralph container does not have, so they run on the macOS host after the merge.

Use the single-element `--env=NAME` form, not the pair `"-e", "NAME"`. Upgrade U4 rewrites a project's devcontainer.json through `merge-runargs.sh`, which drops every project runArgs element the template already has: with `"-e"` in the template, a project with its own `"-e", "FOO"` would lose its `"-e"` and hand `"FOO"` to docker run as a stray argument, which breaks container creation.

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

- `.devcontainer/devcontainer.json` (exists): remove the containerEnv token entry, add `"--env=CLAUDE_CODE_OAUTH_TOKEN"` to runArgs, which stays on its single line.
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
- [x] #1 Neither .devcontainer/devcontainer.json nor plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json has a CLAUDE_CODE_OAUTH_TOKEN key in containerEnv, and both list "--env=CLAUDE_CODE_OAUTH_TOKEN" (one element, the name only, no value) in their single-line runArgs, with no separate "-e" element
- [x] #2 A test pins the template's name-only forward and the absent containerEnv entry, a test runs merge-runargs.sh on the template and a project file whose runArgs add "-e", "FOO" and finds both "--env=CLAUDE_CODE_OAUTH_TOKEN" and the project's "-e", "FOO" pair in the output, and uv run pytest and the template-parity bats suite pass
- [ ] #3 On the macOS host after the merge: with CLAUDE_CODE_OAUTH_TOKEN exported in the host shell, a freshly created container from the changed devcontainer.json (devcontainer up) reports a non-zero token length via devcontainer exec sh -c 'printf %s ${#CLAUDE_CODE_OAUTH_TOKEN}', and ps -eo args on the host, grepped with the token read via -f from a umask 077 mktemp file, counts 0; both results are recorded in the task notes
- [ ] #4 On the macOS host: in that container, devcontainer exec claude -p 'Reply with the single word OK' answers rather than reporting Not logged in
- [ ] #5 On the macOS host: with CLAUDE_CODE_OAUTH_TOKEN unset in the host shell, devcontainer up of a fresh container still succeeds and the in-container token length prints 0
- [x] #6 plugins/ralph/skills/ralph-init/SKILL.md describes the token forward as the name-only runArgs entry --env=CLAUDE_CODE_OAUTH_TOKEN and says why: a containerEnv value becomes docker run -e NAME=value, visible in the host's ps for the container's lifetime
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Handoff gate (destination): yellow, clarified with the user. Y1 - the forward is one runArgs element, --env=CLAUDE_CODE_OAUTH_TOKEN, not the pair -e, CLAUDE_CODE_OAUTH_TOKEN: Upgrade U4 writes devcontainer.json through merge-runargs.sh, which drops every project element the template already has, so a template -e would strip a project's own -e and leave its value as a stray docker run argument. AC #1 and AC #2 (new merge-runargs.sh case) changed accordingly. Y2 - AC #3 to #5 need docker and the devcontainer CLI, which the Ralph container lacks; they are marked macOS host and are run there after the merge (the host ps check needs a sandbox bypass).

Plan: drop the containerEnv token entry in both devcontainer.json copies, add the single runArgs element --env=CLAUDE_CODE_OAUTH_TOKEN with a comment on why, rewrite the SKILL.md auth passage, pin it in tests/python/test_devcontainer_oauth_token_forward.py (incl. a merge-runargs.sh case with a project "-e", "FOO" pair).

Commit: `db3d18c` - task-282: forward CLAUDE_CODE_OAUTH_TOKEN by name in runArgs so its value stays off the docker run argv

Done in container: AC #1, #2, #6. Both devcontainer.json copies drop the containerEnv token entry and carry the runArgs element --env=CLAUDE_CODE_OAUTH_TOKEN (commented with the why); SKILL.md auth passage (prerequisites, GUI caveat, graceful degradation, do-not-commit) rewritten for the name-only forward. tests/python/test_devcontainer_oauth_token_forward.py (8 tests) pins the forward, the absent containerEnv key, a mutation, a real merge-runargs.sh run keeping a project "-e", "FOO" pair, and the SKILL.md wording. uv run pytest 921 passed/3 skipped; ruff clean; template-parity.bats 11/12 - test 5 (settings.local.json shape) fails identically on master: in the container .claude/settings.local.json is the overlay lacking the template's attribution key, unrelated. task-reviewer: APPROVED (0 findings). PENDING on the macOS host after merge: AC #3, #4, #5 (devcontainer up / exec / host ps check) - record their results here and check them off.

Commit: `733b8b7` - task-282: bump plugin version to 0.14.9 (patch)
<!-- SECTION:NOTES:END -->
