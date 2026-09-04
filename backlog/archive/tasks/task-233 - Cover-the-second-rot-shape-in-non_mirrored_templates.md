---
id: TASK-233
title: Cover the second rot shape in non_mirrored_templates
status: To Do
assignee: []
created_date: '2026-09-04 11:23'
updated_date: '2026-09-04 13:34'
labels: []
dependencies:
  - TASK-230
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up to TASK-230, from the task-reviewer's one non-blocking finding.

TASK-230's description named two ways a `non_mirrored_templates()` entry can rot:

(a) the template it names was deleted or renamed;
(b) the template later gained a live counterpart and should have been promoted to a registry row.

TASK-230's AC #1 asked only for (a) -- "matches at least one real path" -- and the shipped guard `R11: every non_mirrored_templates entry still matches a template path` covers exactly that. Shape (b) is still unguarded: an exemption whose template acquires a live twin keeps its exemption forever, and the closure test at `tests/unit/template-parity.bats` never notices because it short-circuits on `in_registry "$rel" && continue` before it ever consults the list.

The sibling list does not have this hole. For `repo_local_hooks()`, shape (b) is caught indirectly: adding `templates/claude/hooks/<name>.sh` without a registry row trips the pre-existing unregistered-template closure test.

The reviewer checked all six current exemptions -- claude/task-reviewer-rules.docs.md, devcontainer/Dockerfile.base, devcontainer/lang/, obsidian/, root/CLAUDE.conventions.docs.md, root/CLAUDE.conventions.python.md -- and found no live counterpart for any of them. Nothing is broken today; this closes the shape before it bites.

Two candidate guards, either or both:

1. **Dual-listing.** A template path that is BOTH in the registry and matched by `non_mirrored_templates()` has a dead exemption -- the promotion happened and the old row was left behind. Cheap: intersect the two lists. Note the closure walk's `in_registry ... && continue` ordering means such an entry is silently unreachable today.
2. **Live-counterpart probe.** For each non-subtree exemption, derive the live path the registry's own conventions imply (claude/X -> .claude/X, root/X -> X, devcontainer/X -> .devcontainer/X, git-hooks/X -> .git/hooks/X) and fail if that file exists on disk but the pair is unregistered. Stronger, but it must not fire on the four `.docs.md` / `.conventions.*` starters, whose whole point is that they have no live twin under that name.

Prefer (1) if (2) cannot be made to pass cleanly on today's six entries without a second exemption list -- an exemption list for the exemption list would defeat the purpose.

**Out of scope:** the anti-vacuity floors on the two TASK-230 guards (the reviewer verified `-ge 3` / `-ge 2` are deliberately loose so retiring a legitimate exemption does not force an unrelated edit, and that the pre-existing closure tests cross-brace them); any change to `claude_md_allowed_deviations()`, which already has its stale-entry guard.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A dual-listed template path -- present in registry() and matched by non_mirrored_templates() -- fails the suite with a message naming the entry and saying to delete the exemption
- [ ] #2 The guard is proved non-vacuous by mutation: adding a registry row for one of today's six exemptions makes the suite fail, and reverting restores green
- [ ] #3 If the live-counterpart probe (option 2) is implemented, it passes on all six current entries with no new exemption list; if it is not, the task notes state why it was rejected
- [ ] #4 Full suite stays green: LC_ALL=C node_modules/.bin/bats tests/unit tests/integration tests/e2e reports 0 failures
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Won't do: closed as diminishing-returns tail of the 227-235 review chain. The ecryptfs filename problem is fully solved by TASK-227 (prevention) + TASK-231 (remediation); this task is edge-of-edge test/normalizer coverage with no real-world impact. Archived rather than implemented.
<!-- SECTION:NOTES:END -->
