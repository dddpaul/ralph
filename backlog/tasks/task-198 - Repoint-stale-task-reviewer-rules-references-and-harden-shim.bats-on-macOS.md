---
id: TASK-198
title: Repoint stale task-reviewer-rules references and harden shim.bats on macOS
status: To Do
assignee: []
created_date: '2026-07-04 06:23'
labels:
  - 'feature:ralph-marketplace'
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up from the ralph-marketplace feature review (design/ralph-marketplace-review-2026-07-04.md, Verdict: Aligned). Two non-blocking hygiene items the cumulative review surfaced, both outside the in-scope ACs of TASK-187..197.

Item 1 — stale references in .claude/task-reviewer-rules.md. TASK-195 correctly repointed only the R11 parity table to plugins/ralph/skills/ralph-init/templates/... The R16 section and the header/loading narrative (around lines 3, 186, 206) still name top-level agents/ and skills/ paths. Repoint those to plugins/ralph/agents/... and plugins/ralph/skills/... Leave the R11 table as-is (already correct). Verify grep-clean with:

```
grep -nE "(^|[^a-zA-Z/])(agents|skills)/ralph" .claude/task-reviewer-rules.md
grep -nE "agents/(task-reviewer|ralph-reviewer)[.]md" .claude/task-reviewer-rules.md
```

After the fix these should match only plugins/ralph/... forms.

Item 2 — shim.bats resolver tier-2 false-fails on macOS. setup_test_dir uses mktemp under /var/folders/... which is a symlink to /private/var/... The shim sets RALPH_PROJECT_ROOT via pwd -P (canonical /private/var/...), while the test builds the expected orchestrator path from the non-canonical /var/... mktemp path, so the tier-2 expected-vs-actual comparison mismatches. Tiers 4/5 and the byte-identity test pass; this is a test-harness canonicalization nit, not a resolver defect. Fix by canonicalizing the temp dir in tests/helpers/common.bash setup_test_dir, e.g.:

```
TEST_DIR="$(cd "$(mktemp -d)" && pwd -P)"
```

so the expected path matches the shim canonicalized RALPH_PROJECT_ROOT on macOS and Linux.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 R16 and header/loading-narrative path references in .claude/task-reviewer-rules.md are repointed from top-level agents/ and skills/ to plugins/ralph/agents/ and plugins/ralph/skills/
- [ ] #2 grep confirms no stale top-level agents/ or skills/ralph file-path references remain in .claude/task-reviewer-rules.md, and the R11 parity table still points at plugins/ralph/skills/ralph-init/templates/
- [ ] #3 tests/helpers/common.bash canonicalizes the test temp dir with pwd -P or realpath so shim.bats resolver tier-2 no longer false-fails on macOS
- [ ] #4 Full bats suite passes on macOS (bats tests/)
- [ ] #5 uv run pytest passes
- [ ] #6 uv run ruff check . passes
<!-- AC:END -->
