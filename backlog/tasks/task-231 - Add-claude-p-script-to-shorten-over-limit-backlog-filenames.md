---
id: TASK-231
title: Add claude -p script to shorten over-limit backlog filenames
status: Done
assignee: []
created_date: '2026-09-04 06:44'
updated_date: '2026-09-04 07:13'
labels:
  - 'feature:shorten-backlog-filenames'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Direction:** Option A — a self-contained Python PEP 723 script `scripts/shorten-backlog-filenames.py`, run via `uv run`, that renames over-limit backlog markdown files using a `claude -p`-derived semantic slug, with code-side normalization as the correctness guarantee. Dry-run by default; `--apply` does `git mv`.

**Locked decisions (with rationale):**
- **Backlog-aware, filename-only.** *Rationale:* backlog.md addresses artifacts by `id:` frontmatter not filename (proven in TASK-227), so regenerating just the slug is safe and needs no reference rewriting; `title:` is left as the historical record.
- **Dry-run default + `--apply` via `git mv`.** *Rationale:* the script renames in place, so nothing changes until explicitly applied; `git mv` preserves history and stages cleanly.
- **Structured `claude -p` prompt + untrusted-output normalizer.** *Rationale:* the prompt is best-effort; a defensive normalizer (lowercase, drop non-`[a-z0-9-]`, collapse/trim hyphens, cut to budget at a hyphen boundary) is what actually guarantees a valid slug — same philosophy as the shipped guard.
- **Fallback never skips.** *Rationale:* on claude error/timeout/empty-after-retry, truncate the existing slug to budget so the file always ends up under the limit; dry-run tags the row `FALLBACK` for hand-fixing.
- **Per-file slug budget = `limit - len(prefix) - len(".md")`.** *Rationale:* `task-` vs `decision-` prefixes and id widths differ, so the budget must be computed per file, not globally.
- **Byte measurement under `LC_ALL=C`.** *Rationale:* ecryptfs limits bytes, not characters; a UTF-8 locale under-counts multibyte names.
- **Collision suffixing with re-trim.** *Rationale:* a `-2`/`-3` suffix eats into the budget, so the slug must be re-trimmed to keep the final basename <= limit; a per-run planned-targets set prevents same-run clashes.
- **Output <=125 by construction -> passes the TASK-227 pre-commit guard.** *Rationale:* remediation tool and guard are designed to agree; re-runs are idempotent/convergent.
- **Archive/completed excluded by default; `title:` untouched; not shipped in plugin.** *Rationale:* historical files and records stay stable; this is a repo-level one-off.

**Scope cuts:**
- No `title:` rewrite, no archive by default, no interactive per-file confirm, no reference rewriting, not plugin-distributed.

**Implementation checklist:**
- Write `scripts/shorten-backlog-filenames.py` (PEP 723 uv metadata; argparse CLI: default dry-run, `--apply`, `--limit`, `--model`, `--path`, `--include-archive`).
- Pure functions: `basename_bytes` (LC_ALL=C), `parse_prefix` (`<type>-<id> - ...\.md`), `slug_budget`, `normalize_slug`, `dedupe_target`.
- I/O layer: walk backlog dirs, bounded content slice, `claude -p` subprocess (timeout, `--model`), `git mv`.
- Retry-once + fallback-truncate logic; `FALLBACK`/`COLLISION` markers in dry-run table; end-of-run summary.
- Tests in `tests/` (pytest): normalizer table, budget/parse/collision/byte-length units, one stubbed-claude integration test.
- Run `uv run pytest` + `uv run ruff check .`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 scripts/shorten-backlog-filenames.py exists; `uv run scripts/shorten-backlog-filenames.py` runs a dry-run that prints planned old -> new for every over-limit backlog file and changes nothing on disk or in git
- [x] #2 --apply renames via git mv; already-short files are skipped; files whose names do not match the <type>-<id> - <slug>.md shape are skipped with a warning
- [x] #3 Basename byte length is measured under LC_ALL=C; default limit is 125; the per-file slug budget subtracts the <type>-<id> - prefix and the .md suffix
- [x] #4 claude -p output is normalized to [a-z0-9-] and trimmed to the budget at a hyphen boundary; empty or too-short results trigger exactly one retry, then a FALLBACK truncation of the existing slug (a file is never skipped for being over-limit)
- [x] #5 Target-name collisions get a numeric suffix with the slug re-trimmed so the final basename stays <= limit, and no two source files map to the same target in one run
- [x] #6 Every output filename satisfies the TASK-227 pre-commit filename-length guard, and re-running the script is idempotent (a second run proposes no further renames)
- [x] #7 pytest covers the normalizer with a table of messy claude outputs, plus budget math, prefix parse, collision suffixing, and multibyte byte-length; one integration test uses a throwaway git repo with fixture files and a stubbed claude subprocess to assert dry-run output and that --apply performs the expected git mv
- [x] #8 uv run pytest and uv run ruff check . both pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) scripts/shorten-backlog-filenames.py — PEP 723 stdlib-only script, no shebang, matching tests/scripts/check_run_clean.py. Pure layer: basename_bytes (os.fsencode == LC_ALL=C byte count), parse_prefix (regex over '<kind>-<id> - <slug>.md', dotted ids allowed), slug_budget (limit - prefix bytes - '.md'), trim_to_budget (byte-safe cut, then back off to the last hyphen), normalize_slug (first non-fence non-empty line -> lower -> whitespace/underscore to hyphen -> drop non [a-z0-9-] -> collapse -> trim), dedupe_target (-2/-3 suffix with slug re-trim so the basename stays <= limit). (2) I/O layer: collect_files over backlog/{tasks,docs,decisions,drafts} (+archive,completed under --include-archive), content_slice (frontmatter title + bounded body), ask_claude ('claude -p --model M <prompt>', 60s timeout, stdout untrusted), git mv via 'git -c safe.directory=<root> -C <root> mv'. (3) propose_slug: 2 attempts (= exactly one retry) then FALLBACK truncation of the existing slug, so no over-limit file is ever skipped. (4) CLI: dry-run default, --apply, --limit 125, --model, --path, --include-archive; per-file two-line old -> new report with [OK]/[FALLBACK]/[COLLISION] markers and an end-of-run summary; exit 1 only if a git mv errored. (5) Tests at tests/python/test_shorten_backlog_filenames.py (new dir added to pyproject testpaths, since testpaths currently pins only the plugin tests); normalizer table, budget/parse/collision/multibyte units incl. a bash LC_ALL=C parity assertion, plus throwaway-git-repo integration tests with a stubbed claude on PATH covering dry-run/--apply/idempotency/fallback-retry-count. (6) uv run pytest + uv run ruff check . (baseline: 346 passed, ruff clean).

Commit: `cc2f7c9` - task-231: add claude -p script to shorten over-limit backlog filenames

Implemented. scripts/shorten-backlog-filenames.py (PEP 723, stdlib-only, not shipped in the plugin) walks backlog/{tasks,docs,decisions,drafts} (+archive,completed under --include-archive), measures each basename in bytes via os.fsencode (the LC_ALL=C measurement filename-length-guard.sh uses), and for every name over --limit (default 125) asks 'claude -p --model <model>' for a shorter slug, normalizes the untrusted answer to [a-z0-9-] and trims it to the per-file budget (limit - prefix bytes - '.md') at a hyphen boundary. Two attempts (= exactly one retry), then a FALLBACK truncation of the existing slug, so an over-limit file is never skipped. Collisions take a -2/-3 suffix paid for out of the slug, and a per-directory claimed set (seeded from the on-disk glob) keeps two sources in one run from mapping to one target. Dry run is the default; --apply renames with 'git mv -c safe.directory=<resolved root>'. Only the filename changes: the <type>-<id> - prefix, the .md suffix and the title: frontmatter are untouched, which is safe because backlog.md addresses artifacts by id:. Tests: tests/python/test_shorten_backlog_filenames.py, 61 tests -- normalizer table (fences, quotes, prose, all-Cyrillic -> empty), budget/parse/collision/multibyte units incl. a bash '${#name}'-under-LC_ALL=C parity assertion, and 8 CLI runs over a throwaway git repo with a stubbed claude on PATH covering dry-run/--apply/idempotency/archive-opt-in/retry-count. AC #6 is proven by running the real .claude/hooks/filename-length-guard.sh against the staged renames (the reviewer independently confirmed that assertion is non-vacuous). pyproject.toml testpaths gained tests/python (it previously pinned only the plugin suite); README documents the 125-byte cap, the script and the new pytest root. Gates: uv run pytest 407 passed (346 on master + 61 new), uv run ruff check . clean, bats 163 passed. Environment limit: the container's claude CLI is not logged in, so a SUCCESSFUL live claude -p call could not be exercised here -- the failure path was exercised for real (exit 1 -> retry -> FALLBACK, file still landed at 122 bytes) and the success path is covered by the stub. task-reviewer verdict: APPROVED, with 5 non-blocking findings (prose-preamble slugs, untracked-file git mv error, missing safe.directory on git_repo_root, backlog/milestones not scanned, minor trivia) filed as a follow-up task rather than fixed post-approval.
<!-- SECTION:NOTES:END -->
