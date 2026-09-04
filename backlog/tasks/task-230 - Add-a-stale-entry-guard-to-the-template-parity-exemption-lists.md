---
id: TASK-230
title: Add a stale-entry guard to the template-parity exemption lists
status: To Do
assignee: []
created_date: '2026-09-04 06:02'
labels: []
dependencies:
  - TASK-229
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
tests/unit/template-parity.bats keeps three hand-maintained exemption lists, but only one of them is self-cleaning.

claude_md_allowed_deviations() has a stale-entry guard: the region test walks every pinned entry and fails if it no longer matches a real deviation, so fixing a pinned DRIFT row forces its deletion. That guard is what made TASK-229's allow-list cleanup mandatory rather than cosmetic.

Its two siblings have no such guard:
- non_mirrored_templates() — an entry naming a template file that was deleted or renamed, or one that later gained a live counterpart and should have become a registry row, stays silently honoured.
- repo_local_hooks() — same: a hook that is removed, or that later gains a template and should be mirrored, keeps its exemption forever.

Both lists are consulted only as 'is this path justified?' lookups, so an obsolete entry is never exercised and never reported. Over time that turns a justified exemption list into a blanket one — exactly the failure mode the claude_md_allowed_deviations guard was written to prevent.

Discovered while implementing TASK-229: a mis-targeted mutation accidentally inserted a bogus row into repo_local_hooks() and the suite stayed 163/163 green.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every non_mirrored_templates() entry is asserted to match at least one real path under plugins/ralph/skills/ralph-init/templates/ (subtree entries ending in / match a non-empty subtree); an entry matching nothing fails with a message naming it
- [ ] #2 Every repo_local_hooks() entry is asserted to name an existing file under .claude/hooks/; an entry naming a missing file fails with a message naming it
- [ ] #3 Each new guard is proved non-vacuous by mutation: adding a bogus entry to either list makes the suite fail, and removing it restores green
- [ ] #4 Full suite stays green: LC_ALL=C node_modules/.bin/bats tests/unit tests/integration tests/e2e reports 0 failures
<!-- AC:END -->
