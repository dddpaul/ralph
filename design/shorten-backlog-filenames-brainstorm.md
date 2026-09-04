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

---

## Addendum: multi-project recursive sweep with per-project commit (added 2026-09-04)

### Why
The shipped script is single-project: `--path` points *at one backlog root* and it only stages (`git mv`), never commits. The real use case is a fleet — dozens of projects, each with its own backlog carrying over-limit filenames — replicated by Syncthing to a Linux ecryptfs volume. Pointing the script at each project by hand does not scale. The operator wants to point it at one parent directory and have it recursively find every project's backlog, and for each project: rename over-limit files via the existing `claude -p` slug logic, commit those renames to that project, then move to the next.

### What changed
The single script gains a **discover → group → per-project loop** shell around the existing per-backlog-root logic. Everything that produces a slug (prompt, normalizer, budget math, dedupe, `git mv`) is reused unchanged; all reused machinery (`git_repo_root`, `git_tracked`, `git_mv`, `plan_renames`, `collect_files`) already exists.

- **Discovery (`discover_projects(root)`):** `os.walk(root)` top-down, pruning `.git`, `node_modules`, `.venv`, `__pycache__`, `.pytest_cache`, `dist`, `build`, and not descending into a backlog root once found. A directory is a **backlog root** iff it contains `config.yml` **and** at least one `SCAN_SUBDIRS` entry (e.g. `tasks/`) — the two-signal test avoids matching unrelated `config.yml` files. `project_name` is read from `config.yml` with a small regex (no YAML dependency — PEP 723 stays stdlib-only), falling back to the repo dir name.
- **Grouping:** each backlog root is resolved to its enclosing git repo via the existing `git_repo_root()`; roots are grouped by repo top-level, so a monorepo with two backlog roots is one project committed once. A backlog root in **no git repo** is skipped with a warning (nothing to commit to; no VCS-less batch renames).
- **New `@dataclass Project`:** `repo_root: Path`, `name: str`, `backlog_roots: list[Path]`. `Rename`/`Counters` reused unchanged; a per-project outcome tally is added.
- **Per-project apply:** collect + `plan_renames` across the project's backlog roots, apply via the existing `git mv` path. **Only tracked files join the commit** — untracked over-limit files are still renamed (`plain_rename`) with the existing NOTICE but not `git add`ed, keeping the shipped script's conservatism about adding brand-new files to a repo unattended.
- **Commit:** if ≥1 tracked rename succeeded, one **pathspec-scoped** commit covering exactly the old+new paths, on the currently-checked-out branch, message fixed at `chore(backlog): shorten N over-limit filename(s) for ecryptfs sync`. New helper `git_commit(repo_root, paths, message, no_verify)` over the existing `run_git`. Pre-existing staged/unstaged changes in the repo are never swept in.
- **Hooks:** commits respect project git hooks by default (so a Ralph project's `commit-prefix-guard` / `filename-length-guard` runs); a new `--no-verify` flag opts into bypassing them for the housekeeping commit.
- **Failure isolation:** a rename or commit failure in one project is reported and the sweep continues; it never aborts the whole run. Exit 1 if any project errored, else 0.
- **Dry-run (default) preserved:** discover + group + plan and print each project's rename rows plus a `Would commit N rename(s) in <name> [<repo_root>]` line; change nothing.
- **Backward compatibility:** default `--path backlog` still yields exactly one project (repo `.`) and behaves as today — the single-project case is the degenerate one-project sweep.

### Implementation checklist
- Add `discover_projects(root)` (os.walk with prune list; two-signal backlog-root test: `config.yml` + a `SCAN_SUBDIRS` entry; regex-read `project_name`), and a `@dataclass Project` grouping backlog roots by `git_repo_root()`; skip non-git roots with a warning.
- Add `git_commit(repo_root, paths, message, no_verify)` over `run_git`; pathspec-scoped to the exact old+new renamed paths.
- Rework `main` into a per-project loop: per project → `collect_files`/`plan_renames` over its backlog roots → apply (tracked via `git mv`, untracked via `plain_rename`+NOTICE, not committed) → one commit of the tracked renames (respecting hooks unless `--no-verify`).
- Add `--no-verify`; widen `--path` help to "a tree to sweep, or a single backlog root". Keep `--apply`/`--limit`/`--model`/`--include-archive`/`--timeout`.
- Extend the summary with `projects=<n> committed=<n> project-errors=<n>`; keep exit 1 on any error.
- Tests (extend existing pytest file): `discover_projects` over a temp tree (2 git-backed projects + decoys: `node_modules/`, stray `config.yml` with no `tasks/`, a backlog root outside git); monorepo grouping (two roots → one Project); pathspec isolation (pre-existing staged change excluded from our commit); `--no-verify` (blocked-then-committed against a failing pre-commit hook); untracked-only project (renamed, NOTICE, no commit); failure isolation (project A fails, B still processed).
- `uv run pytest` + `uv run ruff check .` pass.

### Distilled for ralph-task

**Direction:** Extend `scripts/shorten-backlog-filenames.py` in place into a multi-project recursive orchestrator: given `--path=<tree>`, discover every project's backlog, group by owning git repo, and per project rename over-limit files (reusing the existing `claude -p` slug logic) then commit those renames to that project before moving on. Dry-run stays the default.

**Locked decisions (with rationale):**
- **Always recurse; auto-detect backlog roots.** *Rationale:* one mental model and zero new flags — a single backlog root is just the one-project degenerate case, so today's `--path backlog` keeps working.
- **Backlog root = a directory containing `config.yml` AND at least one `SCAN_SUBDIRS` entry (e.g. `tasks/`).** *Rationale:* `backlog init` always writes `config.yml`; the second signal rejects unrelated `config.yml` files. `project_name` is regex-read from it (no YAML dep — PEP 723 stays stdlib-only), falling back to the repo dir name.
- **Group backlog roots by enclosing git repo (`git_repo_root()`); a monorepo's multiple roots are one project, one commit.** *Rationale:* "commit to this project" means per-repo, not per-backlog-dir.
- **Backlog root in no git repo → skip with a warning.** *Rationale:* there is nothing to commit to; batch mode does not do VCS-less renames.
- **Pathspec-scoped commit of exactly the old+new renamed paths, on the current branch, one per project.** *Rationale:* safe to run unattended over repos you don't inspect — pre-existing staged/unstaged work is never swept in.
- **Fixed message `chore(backlog): shorten N over-limit filename(s) for ecryptfs sync`.** *Rationale:* housekeeping commit; no LLM call needed for the message.
- **Only tracked files join the commit; untracked over-limit files are renamed with the existing NOTICE but not `git add`ed.** *Rationale:* adding a brand-new file to a repo unattended is a bigger action than a rename — keep the shipped script's conservatism.
- **Respect git hooks by default; `--no-verify` opt-in to bypass.** *Rationale:* other Ralph projects' `commit-prefix-guard` blocks non-task commits on master; respecting hooks is the safe default, with an escape hatch for sweeping your own fleet.
- **Failure isolation; exit 1 if any project errored.** *Rationale:* one blocked/failed project must not strand the rest of the sweep.
- **Dry-run remains the default.** *Rationale:* same safety model as the shipped script — nothing changes until `--apply`.

**Scope cuts:**
- No `git add` of untracked files, no VCS-less renames, no per-project branch creation (commit lands on whatever branch is checked out).
- No LLM-generated commit messages; no configurable message.
- No parallelism across projects; no YAML parser dependency; no change to the slug/normalizer/budget/dedupe logic.
- No new limit config surface (125-byte default unchanged).

**Acceptance criteria (sketch):**
- `discover_projects(root)` finds every backlog root under `--path` (dir with `config.yml` + a `SCAN_SUBDIRS` entry), pruning `.git`/`node_modules`/`.venv`/`__pycache__`/`.pytest_cache`/`dist`/`build` and not descending into a found backlog root; decoy `config.yml` (no `tasks/`) and a backlog root outside git are not treated as committable projects.
- Backlog roots are grouped by enclosing git repo; two roots in one repo produce one project committed once; a root in no git repo is skipped with a warning.
- `--apply` performs, per project, the existing renames and then a single pathspec-scoped `git commit` of exactly the old+new tracked-rename paths with the fixed `chore(backlog): …` message; a pre-existing staged unrelated change in that repo is not included in the commit.
- Untracked over-limit files are renamed with the existing NOTICE and are not committed; a project whose only over-limit files are untracked produces no commit.
- Commits respect git hooks by default (a failing hook is reported and that project is skipped without committing); `--no-verify` bypasses hooks and the commit lands.
- A rename/commit failure in one project is reported and the sweep continues; the run exits 1 if any project errored, else 0.
- Default (dry-run) prints per-project grouping, the `old → new` rows, and a `Would commit N rename(s) in <name> [<repo_root>]` line, and changes nothing; `--path backlog` still behaves as the single-project case.
- The end-of-run summary adds `projects=<n> committed=<n> project-errors=<n>` to the existing file tallies.
- `uv run pytest` and `uv run ruff check .` pass.

**Implementation checklist:**
- Add `discover_projects(root)` (os.walk + prune list; two-signal backlog-root test; regex-read `project_name`) and `@dataclass Project(repo_root, name, backlog_roots)`; group by `git_repo_root()`, skip non-git roots with a warning.
- Add `git_commit(repo_root, paths, message, no_verify)` over `run_git`, pathspec-scoped to the exact renamed paths.
- Rework `main` into a per-project loop: `collect_files`/`plan_renames` per project → apply (tracked `git mv`; untracked `plain_rename`+NOTICE, uncommitted) → one hook-respecting (or `--no-verify`) commit of the tracked renames.
- Add `--no-verify`; widen `--path` help; extend the summary with the project tallies; keep exit 1 on any error.
- Extend the pytest file: discovery over a temp tree with decoys, monorepo grouping, pathspec isolation, `--no-verify` blocked-then-committed, untracked-only, failure isolation.
- `uv run pytest` + `uv run ruff check .`.
