---
id: TASK-293
title: >-
  Make the devcontainer locale an installed one: en_US.UTF-8 is exported but not
  generated
status: To Do
assignee: []
created_date: '2026-11-03T17:55:00Z'
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
- [ ] #1 In a recreated container, bash -c true run through devcontainer exec prints no setlocale warning on stderr
- [ ] #2 In that container, python3 -c "import locale; locale.setlocale(locale.LC_ALL, '')" exits 0
- [ ] #3 The test that pins the remoteEnv locale is updated to the chosen value, and uv run pytest and uv run ruff check . pass
<!-- AC:END -->
