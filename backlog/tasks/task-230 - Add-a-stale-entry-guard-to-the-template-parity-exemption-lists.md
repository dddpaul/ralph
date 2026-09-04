---
id: TASK-230
title: Add a stale-entry guard to the template-parity exemption lists
status: Done
assignee: []
created_date: '2026-09-04 06:02'
updated_date: '2026-09-04 11:21'
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
- [x] #1 Every non_mirrored_templates() entry is asserted to match at least one real path under plugins/ralph/skills/ralph-init/templates/ (subtree entries ending in / match a non-empty subtree); an entry matching nothing fails with a message naming it
- [x] #2 Every repo_local_hooks() entry is asserted to name an existing file under .claude/hooks/; an entry naming a missing file fails with a message naming it
- [x] #3 Each new guard is proved non-vacuous by mutation: adding a bogus entry to either list makes the suite fail, and removing it restores green
- [x] #4 Full suite stays green: LC_ALL=C node_modules/.bin/bats tests/unit tests/integration tests/e2e reports 0 failures
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: add two stale-entry guards to tests/unit/template-parity.bats, mirroring the claude_md_allowed_deviations precedent — (1) a test walking non_mirrored_templates() and asserting every entry matches at least one real file under templates/ (trailing-/ entries match a non-empty subtree, via the same quoted-case glob the closure test uses); (2) a test walking repo_local_hooks() and asserting every entry is under .claude/hooks/ and names an existing file. Both report the offending entry by name and carry an anti-vacuity floor on the entry count. Prove non-vacuity by inserting a bogus entry into each list and confirming the suite fails, then reverting to green.

Commit: `1c047f9` - task-230: guard the template-parity exemption lists against stale entries

Implemented: two stale-entry guards in tests/unit/template-parity.bats, mirroring the claude_md_allowed_deviations precedent so both remaining exemption lists are self-cleaning.

- 'R11: every non_mirrored_templates entry still matches a template path' walks the list from the disk side: each entry must match at least one file under plugins/ralph/skills/ralph-init/templates/, with trailing-slash entries matching via the same quoted-case glob the closure test uses (so a subtree entry only passes on a NON-EMPTY subtree, since the walk is over 'find -type f').
- 'R11: every repo_local_hooks entry still names a live hook' asserts both halves: the entry is under .claude/hooks/, and the file exists.
Both report the offending entry by name and carry an anti-vacuity floor on the entry count (>=3 and >=2 over today's 6 and 3), deliberately loose so retiring a legitimate exemption does not force an unrelated edit; mutation M6 below shows the pre-existing closure tests cross-brace the floors.

Non-vacuity (AC #3), four mutations run and reverted, each killing exactly the intended test with a message naming the entry: non_mirrored_templates += '.claude/hooks/not-a-real-hook.sh' and += 'no-such-dir/' both fail the templates guard; repo_local_hooks += '.claude/hooks/not-a-real-hook.sh' fails on the missing file and += 'ralph.sh' fails on the wrong prefix. The first of these reproduces the TASK-229 discovery that motivated this task (a bogus row that left the suite 163/163 green). The reviewer independently re-ran these plus two more ('obsidian/' rewritten without its slash, and the list gutted to one entry) on a scratch copy; both extra shapes are caught, tripping the new guard and the pre-existing closure test together.

Gates: LC_ALL=C node_modules/.bin/bats tests/unit tests/integration tests/e2e -> 165 passing, 0 failing (master baseline 163; the +2 delta is exactly the two new tests). No .py touched, so the ruff/pytest gate is untouched by construction ('git diff master..HEAD -- "*.py"' is empty). R5: only find/sort/case/[ ]/$(( ))/heredocs, no GNU- or BSD-only flags. R11: tests/** is outside the mirror set, so no template counterpart is required.

Review: APPROVED by the task-reviewer agent, with two non-blocking observations. (2) the loose anti-vacuity floors, which the reviewer verified are safe and intentional. (1) is a real gap left open on purpose: the task description names a SECOND rot shape for non_mirrored_templates() — an entry that later gains a live counterpart and should have become a registry row — which AC #1 does not ask for and this guard does not cover. The reviewer checked all six current exemptions and found no latent instance, so nothing is broken today; filed as a follow-up rather than scope-crept into this task. For repo_local_hooks() that shape is already covered indirectly: a new templates/claude/hooks/<name>.sh not in the registry trips the existing unregistered-template closure test.
<!-- SECTION:NOTES:END -->
