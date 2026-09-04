---
id: TASK-235
title: >-
  Reject short affirmative preambles in the shorten-backlog-filenames slug
  normalizer
status: To Do
assignee: []
created_date: '2026-09-04 13:21'
updated_date: '2026-09-04 13:34'
labels:
  - 'feature:shorten-backlog-filenames'
dependencies:
  - TASK-234
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up to TASK-234. The task-reviewer approved TASK-234's refusal stop-list and left one non-blocking gap open, one class over from the refusals it closed.

**The gap.** `pick_slug_line` (scripts/shorten-backlog-filenames.py) now rejects a fallback-pass line of more than `MAX_SLUG_WORDS` (4) words as prose, and rejects a shorter one whose opening token is in `REFUSAL_OPENERS`. A short *affirmative* preamble is neither: it clears the word cap and opens with a word the stop-list does not carry, so it clears `MIN_SLUG_BYTES` and is tagged [OK] with no retry.

Shapes the reviewer verified against the current code:

| raw | words | opening token | normalizes to |
|---|---|---|---|
| `Sure!` | 1 | sure | `sure` |
| `Certainly:` | 1 | certainly | `certainly` |
| `Here is:` | 2 | here | `here-is` |
| `Sure, here it is:` | 4 | sure | `sure-here-it-is` |

Each would name the artifact `task-N - here-is.md`.

Note the standing constraints: `MAX_SLUG_WORDS` cannot simply be lowered (TASK-232 AC #2 pinned a normalizer table containing three-word rows), and TASK-234 AC #3 established that a line already matching `^[a-z0-9][a-z0-9-]*$` must never be second-guessed by a content signal -- pass 1 returns before any stop-list is consulted.

The natural fix is to extend `REFUSAL_OPENERS` into a broader opener stop-list (or add a sibling set) covering affirmative/discourse openers -- `sure`, `certainly`, `here`, `okay`, `ok`, `absolutely`, `of` -- keeping the same first-token-only, fallback-pass-only discipline. Weigh each entry for false positives on a legitimate proposal the same way TASK-234 did.

**Out of scope:** re-prompting with a different prompt, scoring slug quality, lowering MAX_SLUG_WORDS, anything touching the already-conforming first pass.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A short affirmative preamble ('Sure!', 'Certainly:', 'Here is:', 'Sure, here it is:') is rejected by pick_slug_line, with a unit test per shape
- [ ] #2 A test pins that each new shape sits within MAX_SLUG_WORDS, so the word cap cannot be what rejects it
- [ ] #3 A legitimate proposal whose opening token merely starts with a stop word ('Here-doc Parser Fix' -> token 'here-doc') is still accepted, and the existing normalizer table in tests/python/test_shorten_backlog_filenames.py still passes unchanged
- [ ] #4 A line already matching ^[a-z0-9][a-z0-9-]*$ is never rejected by the new signal, even if it is exactly a stop-word token
- [ ] #5 An integration test drives a stub claude that only ever answers with an affirmative preamble and asserts the [FALLBACK] marker plus the truncated original slug in the filename
- [ ] #6 uv run pytest and uv run ruff check . both pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Won't do: closed as diminishing-returns tail of the 227-235 review chain. The ecryptfs filename problem is fully solved by TASK-227 (prevention) + TASK-231 (remediation); this task is edge-of-edge test/normalizer coverage with no real-world impact. Archived rather than implemented.
<!-- SECTION:NOTES:END -->
