---
id: TASK-246
title: Route bats temp dirs through the shared canonicalizing helper
status: Done
assignee: []
created_date: '2026-09-27 12:58'
updated_date: '2026-09-27 13:31'
labels: []
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Ten bats files call `mktemp -d` directly, while `tests/helpers/common.bash` already solves the macOS problem properly in `setup_test_dir`:

```bash
TEST_DIR="$(cd "$(mktemp -d)" && pwd -P)"
```

The canonicalization matters: on macOS `mktemp -d` returns a `/var/folders/...` path that symlinks to `/private/var/...`. Without `pwd -P`, resolved-path comparisons in shim.bats false-fail. The direct callers do not all canonicalize, and none use bats's own `BATS_TEST_TMPDIR`, which is created and cleaned up per test.

Files with a bare `mktemp -d` call: pre-commit-hook, devcontainer-claude-hostpath-bind, devcontainer-python-runtime (x2), pretools-hooks, commit-msg-hook, devcontainer-claude-share, filename-length-guard, version-bump-guard, bump-version, devcontainer-claude-config-root (x2).

Second motivation: in a sandboxed agent session, `mktemp -d` against the system temp dir can fail outright with "Operation not permitted". A `BATS_TEST_TMPDIR`-rooted temp directory is inside the test run's own tree and does not depend on system temp being writable.

## Notes for the implementer

Order matters if this lands alongside the bats-to-pytest port: five of the listed files are slated to move to pytest in a sibling task. Converting them here is still correct — whichever lands first, the other rebases cleanly, since the two changes touch different lines.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tests/helpers/common.bash exposes one shared helper that returns a canonicalized temp directory rooted at BATS_TEST_TMPDIR when that variable is set
- [x] #2 grep -rn 'mktemp -d' over tests/unit and tests/integration returns no hits; every caller goes through the helper
- [x] #3 The macOS pwd -P canonicalization is preserved, so the shim.bats resolved-path comparisons still pass on macOS
- [x] #4 The helper falls back to a plain temp directory when BATS_TEST_TMPDIR is unset, so the files remain runnable outside a bats run
- [x] #5 LC_ALL=C bats tests/unit and bats tests/integration pass with no new failures
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: add make_temp_dir() to tests/helpers/common.bash (mktemp under BATS_TEST_TMPDIR when set, plain mktemp -d otherwise, canonicalized with pwd -P); setup_test_dir uses it; the six remaining unit callers (devcontainer files already moved to pytest by task-247) load common and call it.

Commit: `8483dd2` - task-246: route bats temp dirs through a canonicalizing make_temp_dir helper

Done. Added make_temp_dir() in tests/helpers/common.bash (mktemp -d under BATS_TEST_TMPDIR when set, plain mktemp -d otherwise, canonicalized with pwd -P); setup_test_dir uses it. Six unit files (pre-commit-hook, pretools-hooks, commit-msg-hook, filename-length-guard, version-bump-guard, bump-version) now load common and call it; their duplicate PROJECT_ROOT line was dropped. The devcontainer-* bats files named in the description were deleted by task-247 (ported to pytest), not skipped. Verified: bats unit 110 with only the pre-existing #96 (local settings.local.json drift, fails on master too), integration 52/52, pytest 579 passed, ruff clean; a symlinked BATS_TEST_TMPDIR resolves to the real path. task-reviewer: APPROVED.
<!-- SECTION:NOTES:END -->
