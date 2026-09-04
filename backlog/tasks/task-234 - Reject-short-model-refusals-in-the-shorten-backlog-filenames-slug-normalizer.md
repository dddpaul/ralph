---
id: TASK-234
title: Reject short model refusals in the shorten-backlog-filenames slug normalizer
status: In Progress
assignee: []
created_date: '2026-09-04 11:51'
updated_date: '2026-09-04 13:15'
labels:
  - 'feature:shorten-backlog-filenames'
dependencies:
  - TASK-232
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up to TASK-232. The task-reviewer confirmed the ancestor-chain safe.directory fix and every other AC, and left one non-blocking gap open.

**The gap.** `pick_slug_line` (scripts/shorten-backlog-filenames.py) now rejects a line of more than `MAX_SLUG_WORDS` (4) whitespace-separated words as prose, which catches 'Here is the slug you asked for:' (7 words). A *short* refusal slips under the threshold: `claude -p` answering `I cannot help` (3 words) normalizes to `i-cannot-help`, clears `MIN_SLUG_BYTES`, and is tagged [OK] with no retry -- so the artifact is renamed to `task-N - i-cannot-help.md`. Same defect class as TASK-232 finding 1, just under the word cap.

The word count alone cannot close this: 'Shorten Backlog Filenames' and 'I cannot help' are both three words. A content signal is needed -- e.g. a small stop-list of refusal/first-person openers (`i`, `sorry`, `unable`, `cannot`, `unfortunately`) applied only to the non-kebab fallback pass, so an already-conforming `^[a-z0-9][a-z0-9-]*$` line is never second-guessed.

Note the same threshold reasoning TASK-232 recorded still binds: AC #2 there pinned the existing normalizer table, which contains three-word rows, so the fix must not simply lower MAX_SLUG_WORDS.

**Out of scope:** re-prompting with a different prompt, scoring slug quality, anything touching the already-conforming first pass.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A short first-person refusal such as 'I cannot help' or 'Sorry, I am unable to do that' is rejected by pick_slug_line, with a unit test per shape
- [x] #2 A three-word legitimate proposal ('Shorten Backlog Filenames') is still accepted and the existing normalizer table in tests/python/test_shorten_backlog_filenames.py still passes unchanged
- [x] #3 A line already matching ^[a-z0-9][a-z0-9-]*$ is never rejected by the new signal, even if it starts with a stop-word token
- [x] #4 An integration test drives a stub claude that only ever refuses and asserts the [FALLBACK] marker plus the truncated original slug in the filename
- [x] #5 uv run pytest and uv run ruff check . both pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: add a REFUSAL_OPENERS stop-list to scripts/shorten-backlog-filenames.py and consult it only in pick_slug_line's second (non-kebab fallback) pass, matching the line's FIRST whitespace token after lowercasing, stripping surrounding punctuation and collapsing apostrophes ('I'm' -> im), so 'I cannot help' returns '' and routes to retry+FALLBACK. Pass 1 (CLEAN_SLUG_RE) returns before the check, so an already-conforming kebab line is never second-guessed (AC #3). MAX_SLUG_WORDS stays 4, keeping the TASK-232 normalizer table green (AC #2). Tests: parametrised refusal shapes + a guard asserting the short ones are under the word cap (so the opener signal, not MAX_SLUG_WORDS, is what rejects them), an accept-case for 'Shorten Backlog Filenames', an AC #3 case for a kebab line opening with a stop-word token, and an integration test with a stub claude that only ever refuses asserting [FALLBACK] and the truncated original slug.
<!-- SECTION:NOTES:END -->
