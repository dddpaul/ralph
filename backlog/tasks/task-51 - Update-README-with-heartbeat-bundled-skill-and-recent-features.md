---
id: TASK-51
title: 'Update README with heartbeat, bundled skill, and recent features'
status: Done
assignee:
  - '@claude'
created_date: '2026-04-21 17:06'
updated_date: '2026-04-21 17:48'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
README needs updates for features added in tasks 26-50: (1) Heartbeat-based liveness check — backlog/.ralph-heartbeat file, 5s interval, used by ralph-status and ralph-run instead of kill -0. (2) ralph.sh bundled in ralph-run skill at scripts/ralph.sh with local override fallback. (3) PROJECT_DIR replaces SCRIPT_DIR (symlink-safe, pwd-based). (4) Double-run guard in ralph.sh. (5) --help and --version flags. (6) set -u (nounset) enabled. (7) RALPH_SOURCE_ONLY guard for testing.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 README documents heartbeat liveness mechanism
- [x] #2 README documents bundled ralph.sh in skill with local override
- [x] #3 README documents --help and --version flags
- [x] #4 README documents double-run guard behavior
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Update README.md with four new sections covering: (1) heartbeat liveness mechanism, (2) bundled ralph.sh in skill with local override, (3) --help and --version flags, (4) double-run guard. Will add these as subsections under the existing 'Critical Concepts' section where related concepts already live.

Commit: `88519a7` - task-51: Document heartbeat, bundled skill, double-run guard, and CLI flags in README

Implemented: Added four new subsections under Critical Concepts in README.md — Heartbeat Liveness, Bundled ralph.sh, Double-Run Guard, --help and --version. All content verified against ralph.sh source code. Files changed: README.md.
<!-- SECTION:NOTES:END -->
