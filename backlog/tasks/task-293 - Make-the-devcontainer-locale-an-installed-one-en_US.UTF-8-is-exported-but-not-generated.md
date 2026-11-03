---
id: TASK-293
title: >-
  Make the devcontainer locale an installed one: en_US.UTF-8 is exported but not
  generated
status: Done
assignee: []
created_date: '2026-11-03T17:55:00Z'
updated_date: '2026-11-03T18:49:00Z'
labels: []
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

TASK-290 moved the locale from the user-env probe to remoteEnv (LANG and LC_ALL = en_US.UTF-8, the value ~/.zshrc from zsh-in-docker exports). In the container, locale -a lists only C, C.utf8 and POSIX: en_US.utf8 is not generated. So every process sees a locale that does not exist: bash prints 'setlocale: LC_ALL: cannot change locale (en_US.UTF-8)', perl warns 'Setting locale failed' and falls back to C, and Python's locale.setlocale(locale.LC_ALL, '') raises locale.Error. This was already true before TASK-290 (the probe supplied the same value), and TASK-290 kept it to avoid changing behaviour.

## Options

- Generate the locale in Dockerfile.base (locales package, sed the en_US.UTF-8 line in /etc/locale.gen, locale-gen). Assembled Dockerfiles do not upgrade through U4, so existing projects need a U2 patch offer.
- Or switch remoteEnv to C.UTF-8, which is already installed and needs no image change.

## Files

- plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json (exists)
- .devcontainer/devcontainer.json (exists)
- tests/python/test_devcontainer_oauth_token_forward.py (exists): pins the current locale value
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 In a recreated container, bash -c true run through devcontainer exec prints no setlocale warning on stderr
- [x] #2 In that container, python3 -c "import locale; locale.setlocale(locale.LC_ALL, '')" exits 0
- [x] #3 The test that pins the remoteEnv locale is updated to the chosen value, and uv run pytest and uv run ruff check . pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: switch remoteEnv LANG/LC_ALL to C.UTF-8 (already installed in the base image, no Dockerfile change, upgrades via the normal devcontainer.json template diff) in both copies, update the pinned test and the SKILL.md probe paragraph.

Evidence in this container (same image): with en_US.UTF-8 bash prints 'setlocale: LC_ALL: cannot change locale' and Python raises locale.Error; with C.UTF-8 bash -c true prints nothing on stderr and locale.setlocale(LC_ALL, '') succeeds. AC1/AC2 literally require a recreated container via devcontainer exec, which can only be done from the host — left unchecked for host verification.

Commit: `9c0e1e2` - task-293: set the devcontainer remoteEnv locale to the installed C.UTF-8

Commit: `6ce2d07` - task-293: describe the C.UTF-8 remoteEnv locale in the devcontainer comment

Review: task-reviewer APPROVED (score 9); minor finding on the stale devcontainer.json comment fixed in both copies. Final: uv run pytest 1015 passed / 3 skipped, ruff clean. AC1/AC2 deferred to the macOS host: recreate the container and run 'devcontainer exec ... bash -c true' (expect empty stderr) and the python3 setlocale one-liner (expect exit 0).

Commit: `6519dcb` - task-293: bump plugin version to 0.14.14 (patch)

macOS host verification (after merge, master 0.14.14): devcontainer up --remove-existing-container succeeded (outcome success). AC #1: devcontainer exec --workspace-folder . bash -c true gave rc 0 with 0 bytes on stderr. AC #2: devcontainer exec python3 -c "import locale; locale.setlocale(locale.LC_ALL, '')" gave rc 0 with an empty stderr, and the effective locale prints C.UTF-8. Also checked: LANG=C.UTF-8 and LC_ALL=C.UTF-8 in the exec; locale -a lists C, C.utf8 and POSIX; perl -e 1 runs silently; both tokens are still present (oauth 108, mcp 64). Host gates on master: ruff clean, uv run pytest 1014 passed / 4 skipped, LC_ALL=C bats tests/unit 203/203.
<!-- SECTION:NOTES:END -->
