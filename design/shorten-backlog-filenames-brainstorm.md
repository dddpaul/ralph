# Shorten Backlog Filenames (claude -p remediation)

## Architecture decision

A one-off remediation script — the retroactive counterpart to the TASK-227 filename-length guard. The guard blocks *new* over-limit names; this script fixes *existing* backlog markdown files whose basenames already exceed the byte budget, by having `claude -p` read each file's content and propose a concise, semantic kebab-case slug. **Chosen form:** a self-contained Python PEP 723 script run via `uv run`, with a structured `claude -p` prompt plus code-side normalization/validation as the real correctness guarantee (Option A folding in Option C's structured-output idea).

Scope is **backlog-aware** and **filename-only**: preserve the `<type>-<id> - ` prefix and `.md`, regenerate only the slug, and never touch `title:` frontmatter (the historical record). This is safe because backlog.md addresses artifacts by the `id:` frontmatter, not by filename — proven during TASK-227 (`backlog task edit -t` changes title but not filename; task-215 carried a stale slug with no ill effect).

## Components / flows

- **`scripts/shorten-backlog-filenames.py`** (new) — PEP 723 inline `uv` metadata; stdlib + `claude` CLI + `git` only. Not part of the shipped plugin.
- **CLI:** default = dry-run (print `old → new`, change nothing); `--apply` performs `git mv`; `--limit N` (default 125); `--model NAME` (default a fast model, Haiku); `--path DIR` (default `backlog/`); `--include-archive` (default off).
- **Walk:** `backlog/{tasks,docs,decisions,drafts}/*.md`. Archive/completed excluded by default (historical).
- **Per file:** measure basename bytes under `LC_ALL=C`; `≤ limit` → skip. Parse `<type>-<id> - ` prefix + `.md`; unparseable → skip with warning. Compute per-file slug budget = `limit − len(prefix) − len(".md")`.
- **claude -p contract:** bounded input slice (frontmatter title + description + first AC, ~2–3 KB cap); subprocess with ~60 s timeout; prompt demands ONLY a kebab-case slug ≤ budget. Output treated as untrusted → normalizer: first non-empty line → lowercase → spaces→hyphens → drop non `[a-z0-9-]` → collapse hyphens → trim to budget at a hyphen boundary → strip edge hyphens. Empty/too-short → retry once → else fall back to truncating the existing slug (row tagged `FALLBACK`).
- **Collision:** if target exists on disk or is claimed this run, append `-2`/`-3`/… and re-trim slug to keep ≤ limit. Per-run set of planned targets prevents same-run clashes.
- **Rename:** `git mv`. Output names are ≤125 by construction, so the TASK-227 pre-commit guard passes. Re-runs are convergent/idempotent.
- **Summary:** scanned / over-limit / renamed / fallbacks / collisions.

## Scope cuts

- No `title:` frontmatter rewrite (filename-only).
- No archive/completed by default.
- No interactive per-file confirm (dry-run + `--apply` is the safety model).
- Not shipped in the plugin; a repo-level one-off.
- No reference-rewriting — backlog addresses by id, not filename, so no links/stamps need updating.

## Open questions

- None blocking. Language (Python/uv), scope (backlog-aware, filename-only), safety (dry-run default), and the claude-p contract (structured + normalize + fallback) are locked.

## Hand-off

Next: single ad-hoc task via `ralph-task` (not PRD-shaped — one cohesive deliverable).

## Distilled for ralph-task

**Direction:** Option A — a self-contained Python PEP 723 script `scripts/shorten-backlog-filenames.py`, run via `uv run`, that renames over-limit backlog markdown files using a `claude -p`-derived semantic slug, with code-side normalization as the correctness guarantee. Dry-run by default; `--apply` does `git mv`.

**Locked decisions (with rationale):**
- **Backlog-aware, filename-only.** *Rationale:* backlog.md addresses artifacts by `id:` frontmatter not filename (proven in TASK-227), so regenerating just the slug is safe and needs no reference rewriting; `title:` is left as the historical record.
- **Dry-run default + `--apply` via `git mv`.** *Rationale:* the script renames in place, so nothing changes until explicitly applied; `git mv` preserves history and stages cleanly.
- **Structured `claude -p` prompt + untrusted-output normalizer.** *Rationale:* the prompt is best-effort; a defensive normalizer (lowercase, drop non-`[a-z0-9-]`, collapse/trim hyphens, cut to budget at a hyphen boundary) is what actually guarantees a valid slug — same philosophy as the shipped guard.
- **Fallback never skips.** *Rationale:* on claude error/timeout/empty-after-retry, truncate the existing slug to budget so the file always ends up under the limit; dry-run tags the row `FALLBACK` for hand-fixing.
- **Per-file slug budget = `limit − len(prefix) − len(".md")`.** *Rationale:* `task-` vs `decision-` prefixes and id widths differ, so the budget must be computed per file, not globally.
- **Byte measurement under `LC_ALL=C`.** *Rationale:* ecryptfs limits bytes, not characters; a UTF-8 locale under-counts multibyte names.
- **Collision suffixing with re-trim.** *Rationale:* a `-2`/`-3` suffix eats into the budget, so the slug must be re-trimmed to keep the final basename ≤ limit; a per-run planned-targets set prevents same-run clashes.
- **Output ≤125 by construction → passes the TASK-227 pre-commit guard.** *Rationale:* remediation tool and guard are designed to agree; re-runs are idempotent/convergent.
- **Archive/completed excluded by default; `title:` untouched; not shipped in plugin.** *Rationale:* historical files and records stay stable; this is a repo-level one-off.

**Scope cuts:**
- No `title:` rewrite, no archive by default, no interactive per-file confirm, no reference rewriting, not plugin-distributed.

**Acceptance criteria (sketch):**
- `scripts/shorten-backlog-filenames.py` exists; `uv run scripts/shorten-backlog-filenames.py` runs a dry-run that prints planned `old → new` for every over-limit backlog file and changes nothing.
- `--apply` renames via `git mv`; already-short files are skipped; unparseable names skipped with a warning.
- Byte length measured under `LC_ALL=C`; default limit 125; per-file slug budget accounts for the `<type>-<id> - ` prefix and `.md`.
- `claude -p` output is normalized to `[a-z0-9-]`, trimmed to budget at a hyphen boundary; empty/too-short → one retry → else `FALLBACK` truncation of the existing slug (never skipped).
- Collisions get a numeric suffix with slug re-trim so the final basename stays ≤ limit; no two sources map to one target.
- Output names all satisfy the TASK-227 pre-commit guard; re-running the script is idempotent.
- pytest covers the normalizer (tabled messy-input cases), budget math, prefix parse, collision suffixing, multibyte byte-length, plus one integration test over a throwaway git repo + fixture files with a stubbed `claude` subprocess asserting dry-run output and `--apply` `git mv`s.
- `uv run pytest` and `uv run ruff check .` pass.

**Implementation checklist:**
- Write `scripts/shorten-backlog-filenames.py` (PEP 723 uv metadata; argparse CLI: default dry-run, `--apply`, `--limit`, `--model`, `--path`, `--include-archive`).
- Pure functions: `basename_bytes` (LC_ALL=C), `parse_prefix` (`<type>-<id> - …\.md`), `slug_budget`, `normalize_slug`, `dedupe_target`.
- I/O layer: walk backlog dirs, bounded content slice, `claude -p` subprocess (timeout, `--model`), `git mv`.
- Retry-once + fallback-truncate logic; `FALLBACK`/`COLLISION` markers in dry-run table; end-of-run summary.
- Tests in `tests/` (pytest): normalizer table, budget/parse/collision/byte-length units, one stubbed-claude integration test.
- Run `uv run pytest` + `uv run ruff check .`.
