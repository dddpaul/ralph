---
id: TASK-234
title: Reject short model refusals in the shorten-backlog-filenames slug normalizer
status: Done
assignee: []
created_date: '2026-09-04 11:51'
updated_date: '2026-09-04 13:21'
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

Commit: `0457fda` - task-234: reject short model refusals in the backlog slug normalizer

Done. pick_slug_line's fallback pass now applies two signals instead of one: the pre-existing MAX_SLUG_WORDS length check (unchanged at 4, so the TASK-232 normalizer table still binds) and a new content check matching the line's first token against REFUSAL_OPENERS ({i, im, ive, sorry, apologies, unable, cannot, cant, unfortunately}). The new opening_token helper lowercases the first word, drops surrounding punctuation and removes inner apostrophes -- straight and curly -- so 'I'm' and 'I’m' both fold onto 'im' while 'i18n' and 'I/O' stay whole (token match, not prefix match). Pass 1 returns a CLEAN_SLUG_RE line before the stop-list is ever consulted, so AC #3 holds by construction.

Verification: uv run pytest -> 468 passed; uv run ruff check . -> All checks passed. The test-file diff is a pure insertion (116 added, 0 removed), which is AC #2's 'table passes unchanged' literally. Non-vacuity is pinned two ways: test_short_refusals_sit_within_the_word_cap asserts every short-refusal shape is <= MAX_SLUG_WORDS so it cannot pass for the old reason, and a mutation (refusal = False) kills 13 tests including the integration one. AC #1's second shape, 'Sorry, I am unable to do that', is 7 words and would be caught by the word cap alone; it is kept as LONG_REFUSAL, segregated from SHORT_REFUSALS, so it documents the AC without standing in for the new signal.

ruff format --check reports scripts/shorten-backlog-filenames.py as 'would reformat'. Confirmed pre-existing on master: the single hunk is the PEP 758 unparenthesized 'except' rewrite in ask_claude, untouched by this diff, and the project's declared lint gate is ruff check.

task-reviewer verdict: APPROVED, with two non-blocking observations. (1) Short affirmative preambles ('Sure!', 'Here is:', 'Certainly:') are the same defect class one step over and still slip through -- explicitly out of TASK-234's scope ('refusal/first-person openers'), filed as TASK-235. (2) A conforming kebab line that is exactly a stop word AND below MIN_SLUG_BYTES ('i', 'im') misses pass 1 on length and is then rejected by the new signal, which is a literal reading of AC #3's 'never'. Behaviour is identical to master either way: propose_slug gates on basename_bytes(slug) >= MIN_SLUG_BYTES, so both before and after these route to retry then FALLBACK. No regression, so AC #3 is checked as satisfied in substance.

README: the [FALLBACK] sentence now names a refusal alongside an error and a prose sentence as 'nothing usable'.
<!-- SECTION:NOTES:END -->
