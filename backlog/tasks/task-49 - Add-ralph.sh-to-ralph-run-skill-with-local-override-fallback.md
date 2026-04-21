---
id: TASK-49
title: Add ralph.sh to ralph-run skill with local override fallback
status: To Do
assignee: []
created_date: '2026-04-21 05:04'
updated_date: '2026-04-21 05:38'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ship ralph.sh alongside the ralph-run skill so projects don't need a local copy. Three changes: (1) ralph.sh: replace SCRIPT_DIR with PROJECT_DIR=$(pwd) (no -P flag, preserves symlinks for devcontainer). (2) Move ralph.sh to skills/ralph-run/scripts/ralph.sh. (3) ralph-run skill Step 2: add third fallback — check {skill base directory}/scripts/ralph.sh after ./ralph.sh and scripts/ralph/ralph.sh. Local copy takes precedence, skill copy is the fallback.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ralph.sh uses PROJECT_DIR (pwd-based) instead of SCRIPT_DIR for project paths
- [ ] #2 ralph-run skill Step 2 checks ~/.claude/skills/ralph-run/ralph.sh as third fallback
- [ ] #3 Local ./ralph.sh still takes precedence over skill copy
- [ ] #4 All existing tests pass
- [ ] #5 ralph-run works in a project with no local ralph.sh
<!-- AC:END -->
