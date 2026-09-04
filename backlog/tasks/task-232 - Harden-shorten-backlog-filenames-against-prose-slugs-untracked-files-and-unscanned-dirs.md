---
id: TASK-232
title: >-
  Harden shorten-backlog-filenames against prose slugs untracked files and
  unscanned dirs
status: To Do
assignee: []
created_date: '2026-09-04 07:14'
labels:
  - 'feature:shorten-backlog-filenames'
dependencies:
  - TASK-231
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up to TASK-231. The task-reviewer APPROVED `scripts/shorten-backlog-filenames.py` and raised four non-blocking findings plus trivia. Each is a small, independent hardening of the same script.

**1. A prose preamble becomes the filename (script line ~148, `normalize_slug`).** The locked 'first non-empty, non-fence line' rule means a stub emitting `Here is the slug you asked for:\nralph-stop-drain` yields `task-101 - here-is-the-slug-you-asked-for.md`, tagged `[OK]` with no retry, because it clears `MIN_SLUG_BYTES`. Filename safety holds; semantic sanity does not. Fix: prefer the first line already matching `^[a-z0-9][a-z0-9-]*$`, and treat a line of more than two whitespace-separated words as unusable so the retry/FALLBACK path engages.

**2. `--apply` fails on untracked over-limit files (line ~355, `git_mv`).** `git mv` reports `fatal: not under version control`, the row becomes an error and the file stays over-limit. This is a plausible entry path: the pre-commit guard blocks the commit of a freshly created long-named task, leaving it untracked. Fix: either fall back to `Path.rename` (marking the row) or append a 'file is untracked -- git add it first' hint to the error.

**3. `git_repo_root` omits `-c safe.directory=` (line ~341)** while `git_mv` sets it deliberately. Under the container's occasional dubious-ownership state `rev-parse` fails and the user sees the misleading `ERROR: <path> is not inside a git repository`, with every plan counted as an error.

**4. `backlog/milestones/` is never scanned (line ~48).** It is in neither `SCAN_SUBDIRS` nor `ARCHIVE_SUBDIRS`, so an over-limit milestone name is blocked by the pre-commit guard with no remediation path. This matches the four-directory walk TASK-231 locked, so it is a design gap, not a deviation -- decide whether to add it.

**Trivia (fold in if cheap):** `fallback or 'untitled'` (line ~245) can exceed the budget only when `budget < 8` and the slug starts with a 4-byte codepoint (unreachable at --limit 125); `dedupe_target`'s `RuntimeError` (line ~174) escapes as an unhandled traceback after 99 taken suffixes; plan rows go to stdout while WARNING/ERROR go to stderr, so piped output interleaves out of order.

**Out of scope:** rewriting `title:` frontmatter, reference rewriting, shipping the script in the plugin -- all cut in TASK-231 and still cut.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 normalize_slug rejects a multi-word prose line so 'Here is the slug you asked for:' triggers the retry and then FALLBACK instead of becoming the filename, with a test asserting the FALLBACK marker
- [ ] #2 A single-token line already in [a-z0-9-] form is still accepted unchanged, and the existing normalizer table in tests/python/test_shorten_backlog_filenames.py still passes
- [ ] #3 --apply on an untracked over-limit file either renames it or emits an error naming the untracked file and telling the user to git add it first; covered by a test over a throwaway repo with one untracked fixture
- [ ] #4 git_repo_root passes -c safe.directory=<resolved path> like git_mv does
- [ ] #5 A decision on backlog/milestones is recorded: either it joins the scanned set with a test, or the task notes state why it stays out
- [ ] #6 uv run pytest and uv run ruff check . both pass
<!-- AC:END -->
