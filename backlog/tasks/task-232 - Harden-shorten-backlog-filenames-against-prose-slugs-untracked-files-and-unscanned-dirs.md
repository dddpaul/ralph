---
id: TASK-232
title: >-
  Harden shorten-backlog-filenames against prose slugs untracked files and
  unscanned dirs
status: In Progress
assignee: []
created_date: '2026-09-04 07:14'
updated_date: '2026-09-04 11:39'
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
- [x] #1 normalize_slug rejects a multi-word prose line so 'Here is the slug you asked for:' triggers the retry and then FALLBACK instead of becoming the filename, with a test asserting the FALLBACK marker
- [x] #2 A single-token line already in [a-z0-9-] form is still accepted unchanged, and the existing normalizer table in tests/python/test_shorten_backlog_filenames.py still passes
- [x] #3 --apply on an untracked over-limit file either renames it or emits an error naming the untracked file and telling the user to git add it first; covered by a test over a throwaway repo with one untracked fixture
- [x] #4 git_repo_root passes -c safe.directory=<resolved path> like git_mv does
- [x] #5 A decision on backlog/milestones is recorded: either it joins the scanned set with a test, or the task notes state why it stays out
- [x] #6 uv run pytest and uv run ruff check . both pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: five edits to scripts/shorten-backlog-filenames.py, all local to the file. (1) normalize_slug gains a two-pass line picker: first an already-conforming ^[a-z0-9][a-z0-9-]*$ line anywhere in the output (handles the 'preamble then slug on its own line' shape), else the first non-empty non-fence line but ONLY when it is at most MAX_SLUG_WORDS whitespace words -- longer means prose, return '' and let the retry/FALLBACK path run. Threshold is 4, not the 2 the finding suggested, because AC #2 pins the existing normalizer table which contains 3-word rows ('Shorten Backlog Filenames', 'Shorten: Backlog (Filenames)!') and the integration stub emits a 4-word line expected to land [OK]; 4 is the tightest value compatible with both. (2) apply_renames checks git_tracked() first and falls back to Path.rename for untracked files (guarded by a target-exists check so a rename can never clobber), printing a NOTICE that names the file -- the pre-commit guard blocking a fresh long-named task is exactly how a file gets there, so erroring out would leave the user stuck. (3) git_repo_root gains -c safe.directory=<start.resolve()> and now returns (root, detail) so apply_renames prints git's real stderr instead of the blanket 'not inside a git repository'. (4) DECISION: 'milestones' joins SCAN_SUBDIRS -- backlog/milestones is a first-class dir created by backlog init, its m-<id> - <slug>.md names already match NAME_RE, and backlog.md truncates the milestone slug by UTF-16 code units not bytes (verified: 50 units = 50 ASCII / 100 Cyrillic / 100 emoji bytes, so 50 CJK codepoints = 150 bytes), so milestones are NOT self-limiting under the byte cap. Archived milestones are already covered because the archive walk rglobs. (5) Trivia folded in: _cut_bytes on the 'untitled' fallback, dedupe_target's RuntimeError caught at the call site as a skip+WARNING, and a warn() helper that flushes stdout before writing stderr so piped output stays ordered.

DECISION on AC #5 -- backlog/milestones JOINS the scanned set. Evidence: (a) 'backlog init' creates milestones/ alongside tasks/docs/decisions/drafts, so it is a live artifact dir, not an optional one; (b) milestone basenames are 'm-<id> - <slug>.md', which NAME_RE already parses (kind='m'), so only the walk was missing; (c) backlog.md does cap the milestone slug itself, but by UTF-16 code units, not bytes -- verified empirically against the installed CLI by renaming one milestone three times: 50 units came out as 50 ASCII bytes, 100 Cyrillic bytes and 100 emoji bytes (25 surrogate pairs), which puts a 50-codepoint CJK title at 150 bytes and the whole basename at 159, over the 125-byte cap. So milestones are NOT self-limiting under the guard's measurement and would otherwise be blocked at commit with no remediation path. Confirmed end to end: a 162-byte 'm-0 - <17x CJK>.md' fixture is now reported over-limit and planned down to 123 bytes. Archived milestones needed no change -- the archive walk rglobs backlog/archive, so backlog/archive/milestones/ was already covered by --include-archive.
<!-- SECTION:NOTES:END -->
