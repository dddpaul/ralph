---
id: TASK-138
title: Fix pre-commit hook shebang to use env bash (TASK-136 regression)
status: Done
assignee: []
created_date: '2026-06-12 15:05'
updated_date: '2026-06-12 15:20'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Why:** TASK-136 introduced `skills/ralph-init/templates/git-hooks/pre-commit` with shebang `#\!/bin/bash`, which on macOS resolves to system bash 3.2.57. The hook uses `declare -A` (line 36) which requires bash 4+. Result: every `git commit` in this repo (and in any ralphed project initialized with the new template) errors out with:

```
.git/hooks/pre-commit: line 36: declare: -A: invalid option
declare: usage: declare [-afFirtx] [-p] [name[=value] ...]
```

Fix: change the shebang to `#\!/usr/bin/env bash` so $PATH lookup picks up the user's modern bash (e.g. `/opt/homebrew/bin/bash` on macOS, system bash 5+ on most Linux distros). Other Ralph hooks already use this pattern: `commit-msg` uses `#\!/usr/bin/env bash`. The `post-commit` hook also has `#\!/bin/bash` but happens to not use any bash 4+ features, so it works incidentally — out of scope for this task.

**R11 mirror:** the live `.git/hooks/pre-commit` must be updated in lockstep with the template, per the AC-9 convention TASK-136 established.

**Reproducer (before fix):** `git commit --allow-empty -m "test"` in this repo errors out at the declare line. After fix: command succeeds.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-init/templates/git-hooks/pre-commit line 1 is exactly '#\!/usr/bin/env bash'
- [x] #2 .git/hooks/pre-commit line 1 is exactly '#\!/usr/bin/env bash' (R11 mirror)
- [x] #3 diff skills/ralph-init/templates/git-hooks/pre-commit .git/hooks/pre-commit produces no output (byte-identical)
- [x] #4 .git/hooks/pre-commit remains executable (test -x exits 0)
- [x] #5 bash -n on skills/ralph-init/templates/git-hooks/pre-commit exits 0
- [x] #6 tests/unit/pre-commit-hook.bats passes (6 cases green)
- [x] #7 git commit --allow-empty -m 'test' in this repo exits 0 (regression reproducer no longer fires)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Edit skills/ralph-init/templates/git-hooks/pre-commit line 1 from '#!/bin/bash' to '#!/usr/bin/env bash'. (2) Mirror the same edit to .git/hooks/pre-commit (R11 mirror established by TASK-136 AC-9). (3) Verify byte-identical diff, executable bit on .git mirror, bash -n syntax check, bats suite (6 tests), and the regression reproducer 'git commit --allow-empty -m test'.

Reset to To Do for re-launch — prior Ralph autonomous run exited mid-iteration before commit/review/merge (likely 100% account quota hit). Shebang fix already applied to template and live hook in working tree; will be picked up by next Ralph iteration.

task-reviewer APPROVED. Shebang flip verified end-to-end: template + .git mirror byte-identical at #!/usr/bin/env bash; bats 6/6 green; pre-commit hook exits 0 (no declare -A error); empty commit reproducer succeeds.

Commit: `e170c77` - task-138: Fix pre-commit hook shebang to use env bash
<!-- SECTION:NOTES:END -->
