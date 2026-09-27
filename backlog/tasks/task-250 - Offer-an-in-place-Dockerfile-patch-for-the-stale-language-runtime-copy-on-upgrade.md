---
id: TASK-250
title: >-
  Offer an in-place Dockerfile patch for the stale language-runtime copy on
  upgrade
status: Done
assignee: []
created_date: '2026-09-27 14:43'
updated_date: '2026-09-27 15:09'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

TASK-242 fixed a broken interpreter in the devcontainer image by changing the language *fragments*. But `ralph upgrade` lists `.devcontainer/Dockerfile` as **always skipped** ("assembled from fragments, cannot diff meaningfully") in the U2 file table, and nothing in the upgrade flow re-assembles it. Verified: a grep for `python-runtime`, `python:3.14` and `glibc` across the whole ralph-init SKILL.md returns nothing, and U1.6 legacy migration only moves old `tasks/prd-*.md` files.

So **242's image half reaches no existing project.** Every project bootstrapped as Python or Documentation / Mixed before 242 still carries these inlined instructions in its `.devcontainer/Dockerfile`:

```dockerfile
###
### Stage 1: Language Runtime
###
FROM python:3.14 AS python-runtime
```

```dockerfile
# ---- Language Runtime (from multi-stage) ----
COPY --from=python-runtime /usr/local /usr/local
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
```

That `COPY` drops an interpreter linked against a newer glibc into `/usr/local`, ahead of the bookworm base's own `python3` in PATH, so `python3 -c ''` cannot start at all. The current fragments replace the stage with a comment-only banner and keep only the `uv` copy.

Severity is **degraded, not broken**, because 242 had two halves and the other one does propagate: `.git/hooks/pre-commit` is U2 item 6, so upgraded projects get the probe-by-execution normalizer that skips a `python3` which cannot run. Their commits are therefore not rejected — they just have a dead `python3` in the image.

## Direction — copy the shape that already works

TASK-248 hit the same wall and solved it. See the **"Claude Code version pin on upgrade"** note inside `### U4: Apply Updates`, item 2: it acknowledges the Dockerfile is skipped, then offers a confirm-only in-place patch, shows the diff, applies only on a yes, and re-labels the file `skipped (assembled; version pin patched)` in the U5 summary.

Do the same for the language-runtime fragments: detect an assembled Dockerfile still carrying a `COPY --from=<stage> /usr/local /usr/local` whose stage image and the base image do not pin the same Debian suite, offer to replace that region with the current fragment content, apply only on confirmation, and report it in U5. Leave a project that deliberately re-pinned a matching suite alone — `tests/unit/devcontainer-python-runtime.bats` already encodes that invariant generically, so reuse its rule rather than a text match on `python:3.14`.

## Parity

ralph-init SKILL.md must be updated in BOTH Init (Step 3.x, if the init path needs any note) and Upgrade Mode (U1-U5). `.devcontainer/Dockerfile` stays out of the U2 mirror registry — this is an in-place patch, not a new mirror, so do not add it as a parity pair.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Upgrade detects an assembled .devcontainer/Dockerfile that still copies a foreign interpreter over /usr/local and reports it instead of silently skipping the file
- [x] #2 Detection reuses the suite-matching invariant from the existing devcontainer-python-runtime test rather than a text match on a specific image tag, so a deliberate matching re-pin is left alone
- [x] #3 The patch is confirm-only: the diff is shown and nothing is written without an explicit yes, matching the U4 Claude Code version pin precedent
- [x] #4 On a yes, the copied region is replaced with the current language fragment content for the project's detected flavour
- [x] #5 The U5 summary labels the file as patched rather than plain skipped when the patch fires, and says so when the user declines
- [x] #6 ralph-init SKILL.md documents the behaviour in Upgrade Mode, and .devcontainer/Dockerfile is NOT added to the U2 mirror registry
- [x] #7 A test covers both branches: a stale Dockerfile is detected, and one whose stage matches the base suite is not flagged
- [x] #8 LC_ALL=C bats tests/unit, uv run pytest and uv run ruff check . all pass with no new failures
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: ship a read-only detector/patcher plugins/ralph/skills/ralph-init/scripts/stale-runtime-copy.sh (check|patch) implementing the suite-matching rule of tests/python/test_devcontainer_python_runtime.py (the task body names a .bats file; the invariant actually lives in that pytest module). SKILL.md: U2 item 12 runs check, U3 shows it, U4 confirm-only patch offer mirroring the version-pin note, U5 labels, Init 3.6 self-check. Tests in tests/python/test_upgrade_stale_runtime_copy.py run the detector side by side with the guard's check_copies matrix.

Commit: `435059b` - task-250: offer an in-place patch for the stale language-runtime copy on upgrade

Commit: `1e90257` - task-250: bound the patched copy paragraph and handle every patch exit code

Done. Shipped plugins/ralph/skills/ralph-init/scripts/stale-runtime-copy.sh (check|patch, read-only, awk): same suite-matching rule as tests/python/test_devcontainer_python_runtime.py (the task body's .bats name was wrong; the invariant lives in that pytest module), cross-checked on the guard's _repro matrix. patch prints the file with the stale stage/copy paragraph swapped for the current lang/install fragments (flavour from the file: docs marker or python:* stage); exit 3 = patch by hand (multiple copies, unknown stage, copy paragraph mixed with other instructions), exit 2 = unreadable input, prints nothing. SKILL.md: Init 3.6 self-check, U2 item 12 check, U3 pending-work rule, U4 confirm-only offer, U5 labels; Dockerfile stays out of the parity registry. Gates: uv run pytest 620 passed; ruff clean; LC_ALL=C bats tests/unit 1 failure (R11 settings.local.json JSON shape) which fails identically on master baseline (gitignored per-developer file) - no new failures. Only mawk available in-container; BSD awk not exercised. task-reviewer APPROVED after one round (paragraph-walk bound, exit-code handling, U3 contradiction).

Commit: `b0efcad` - task-250: bump plugin version to 0.7.0 (minor)
<!-- SECTION:NOTES:END -->
