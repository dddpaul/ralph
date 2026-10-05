---
id: TASK-274
title: Refresh the Claude block comment when early-claude-arg.sh moves the ARG
status: Done
assignee: []
created_date: '2026-10-05 19:02'
updated_date: '2026-10-05 19:25'
labels: []
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

`plugins/ralph/skills/ralph-init/scripts/early-claude-arg.sh patch` (TASK-273) moves `ARG CLAUDE_CODE_VERSION` and its "No default on purpose" comment paragraph to just before `LABEL dev.ralph.claude-code-version`. It leaves the old npm-step comment where it was, so a patched pre-TASK-272 project ends up with two comment paragraphs stacked under `# ---- Claude ----`. The first of them still makes the claim TASK-272 corrected: that a bump changes only this layer's cache key. Verified in TASK-273 AC #9, where the patched 39adcb5 template reads:

```dockerfile
# ---- Claude ----
# Bumping CLAUDE_CODE_VERSION changes this layer's cache key, so the next
# build reinstalls; the label lets `docker image inspect` report the version.
# No default on purpose: the version comes from devcontainer.json build.args,
# a concrete X.Y.Z. A floating tag like `latest` is resolved once and then
# frozen in the layer cache, so the image silently ages; the npm step below
# refuses one.
ARG CLAUDE_CODE_VERSION
LABEL dev.ralph.claude-code-version="${CLAUDE_CODE_VERSION}"
```

The current `plugins/ralph/skills/ralph-init/templates/devcontainer/Dockerfile.base` has a single comment block between `# ---- Claude ----` and `ARG CLAUDE_CODE_VERSION`. It begins "No default on purpose" and explains that a changed ARG invalidates every later RUN.

## Change

When `patch` moves the ARG, it also replaces the comment lines between `# ---- Claude ----` and the moved `ARG`, but only when those lines are exactly the two known old paragraphs: the pre-TASK-272 npm-step comment quoted above, then the moved "No default on purpose" paragraph. The replacement is the comment block taken from the shipped `Dockerfile.base`, read at run time. Locate the template the way `stale-runtime-copy.sh` locates its fragments (`here=$(cd "$(dirname "$0")" && pwd)`, then `$here/../templates/devcontainer/Dockerfile.base`), so the script holds no second copy that could drift. Any other comment there, such as a project's own note, is kept unchanged and the ARG still moves. A comment is not worth a patch-by-hand exit.

## Out of scope

- A comment-only finding: `check` still reports only ARG placement, so a Dockerfile whose ARG is already in place exits 0 whatever its comments say.
- `broad-sudoers-chown.sh`, U2/U5 labels, and any change to the template itself.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 early-claude-arg.sh patch applied to the 39adcb5 Dockerfile.base assembled as the node flavour yields a block from '# ---- Claude ----' through the npm RUN that is byte-identical to the same block of the current Dockerfile.base — verified by a test
- [x] #2 The replacement comment is read from the shipped Dockerfile.base at run time: grep -F 'invalidates the cache of every RUN' plugins/ralph/skills/ralph-init/scripts/early-claude-arg.sh finds nothing
- [x] #3 A Dockerfile with any other comment between '# ---- Claude ----' and the ARG keeps that comment unchanged while the ARG still moves before the LABEL, and patch exits 0 — verified by a test
- [x] #4 early-claude-arg.sh check still exits 0 on a Dockerfile whose ARG is already in place but carries the old npm-step comment — verified by a test
- [x] #5 The U4 early-ARG offer in plugins/ralph/skills/ralph-init/SKILL.md states that the patch also refreshes the Claude block comment when it is the old text
- [x] #6 On the macOS host, tests/python/test_upgrade_early_claude_arg.py passes with /bin/bash 3.2 and /usr/bin sed, grep and awk first on PATH; the output is recorded in the task notes
- [x] #7 uv run ruff check . is clean, uv run pytest passes and LC_ALL=C node_modules/.bin/bats tests/unit passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: in patch mode, after locating the moved block, test whether the comment lines between '# ---- Claude ----' and the target are exactly the pre-TASK-272 npm-step paragraph AND the moved block's comment is exactly the old 'No default on purpose' paragraph; if so print the comment block read from $here/../templates/devcontainer/Dockerfile.base (lines between the Claude header and ARG) instead of both. Any other comment: keep, move ARG as before. Tests in tests/python/test_upgrade_early_claude_arg.py; SKILL.md U4 step 2 sentence.

Commit: `a1fd69a` - task-274: refresh the pre-TASK-272 Claude block comment when early-claude-arg.sh patch moves the ARG

Review 1 (task-reviewer): CHANGES REQUESTED — AC #6 had no deferral note; minor: CRLF files got LF-only refreshed comment lines. Fixed: the refreshed comment takes the moved ARG's CRLF ending (test_patch_keeps_crlf_line_endings).
AC #6 DEFERRED to the macOS host: this Linux container has no /bin/bash 3.2 or BSD userland (/usr/bin/nawk is mawk; the mawk test passes). Host command: PATH=/usr/bin:/bin:$PATH uv run pytest tests/python/test_upgrade_early_claude_arg.py — record its output here and check AC #6.
Gates: ruff clean; pytest 880 passed, 3 skipped; bats 153/154 — not ok 140 (R11 settings.local.json shape) fails identically on master: it reads the gitignored local .claude/settings.local.json, not touched by this task.

Commit: `51326a8` - task-274: keep CRLF line endings on the refreshed Claude block comment

Review 2 (task-reviewer): APPROVED, no findings. Correction: pytest count is 879 passed, 3 skipped (not 880). Left In Progress and unmerged on task-274: Done/bump/merge wait for the AC #6 macOS host run.

AC #6 host (macOS): PATH=/usr/bin:/bin:$PATH gives bash=/bin/bash 3.2.57(1)-release and sed/grep/awk from /usr/bin. uv run pytest tests/python/test_upgrade_early_claude_arg.py: 32 passed, 1 skipped ('mawk not installed'; that case ran in the container). Real-file check: early-claude-arg.sh patch on the 39adcb5 Dockerfile.base assembled as the node flavour (the TASK-273 AC #9 fixture) exits 0, and its block from '# ---- Claude ----' through the npm RUN is identical to the current Dockerfile.base (diff empty). Host gates: uv run ruff check . clean; uv run pytest 878 passed, 4 skipped; LC_ALL=C node_modules/.bin/bats tests/unit 154 ok, 0 not ok.

Commit: `a380e00` - task-274: bump plugin version to 0.14.1 (patch)
<!-- SECTION:NOTES:END -->
