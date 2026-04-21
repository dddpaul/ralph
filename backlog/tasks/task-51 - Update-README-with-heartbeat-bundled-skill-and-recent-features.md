---
id: TASK-51
title: 'Update README with heartbeat, bundled skill, and recent features'
status: To Do
assignee: []
created_date: '2026-04-21 17:06'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
README needs updates for features added in tasks 26-50: (1) Heartbeat-based liveness check — backlog/.ralph-heartbeat file, 5s interval, used by ralph-status and ralph-run instead of kill -0. (2) ralph.sh bundled in ralph-run skill at scripts/ralph.sh with local override fallback. (3) PROJECT_DIR replaces SCRIPT_DIR (symlink-safe, pwd-based). (4) Double-run guard in ralph.sh. (5) --help and --version flags. (6) set -u (nounset) enabled. (7) RALPH_SOURCE_ONLY guard for testing.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 README documents heartbeat liveness mechanism
- [ ] #2 README documents bundled ralph.sh in skill with local override
- [ ] #3 README documents --help and --version flags
- [ ] #4 README documents double-run guard behavior
<!-- AC:END -->
