---
id: TASK-236
title: >-
  Extend shorten-backlog-filenames.py into a multi-project recursive sweep with
  per-project commit
status: Done
assignee: []
created_date: '2026-09-04 17:12'
updated_date: '2026-09-04 17:40'
labels:
  - 'feature:shorten-backlog-filenames'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Direction:** Extend `scripts/shorten-backlog-filenames.py` in place into a multi-project recursive orchestrator: given `--path=<tree>`, discover every project's backlog, group by owning git repo, and per project rename over-limit files (reusing the existing `claude -p` slug logic) then commit those renames to that project before moving on. Dry-run stays the default.

**Locked decisions (with rationale):**
- **Always recurse; auto-detect backlog roots.** *Rationale:* one mental model and zero new flags — a single backlog root is just the one-project degenerate case, so today's `--path backlog` keeps working.
- **Backlog root = a directory containing config.yml AND at least one SCAN_SUBDIRS entry (e.g. tasks/).** *Rationale:* `backlog init` always writes config.yml; the second signal rejects unrelated config.yml files. project_name is regex-read from it (no YAML dep — PEP 723 stays stdlib-only), falling back to the repo dir name.
- **Group backlog roots by enclosing git repo (git_repo_root()); a monorepo's multiple roots are one project, one commit.** *Rationale:* "commit to this project" means per-repo, not per-backlog-dir.
- **Backlog root in no git repo -> skip with a warning.** *Rationale:* there is nothing to commit to; batch mode does not do VCS-less renames.
- **Pathspec-scoped commit of exactly the old+new renamed paths, on the current branch, one per project.** *Rationale:* safe to run unattended over repos you don't inspect — pre-existing staged/unstaged work is never swept in.
- **Fixed message `chore(backlog): shorten N over-limit filename(s) for ecryptfs sync`.** *Rationale:* housekeeping commit; no LLM call needed for the message.
- **Only tracked files join the commit; untracked over-limit files are renamed with the existing NOTICE but not git add-ed.** *Rationale:* adding a brand-new file to a repo unattended is a bigger action than a rename — keep the shipped script's conservatism.
- **Respect git hooks by default; `--no-verify` opt-in to bypass.** *Rationale:* other Ralph projects' commit-prefix-guard blocks non-task commits on master; respecting hooks is the safe default, with an escape hatch for sweeping your own fleet.
- **Failure isolation; exit 1 if any project errored.** *Rationale:* one blocked/failed project must not strand the rest of the sweep.
- **Dry-run remains the default.** *Rationale:* same safety model as the shipped script — nothing changes until `--apply`.

**Scope cuts:**
- No git add of untracked files, no VCS-less renames, no per-project branch creation (commit lands on whatever branch is checked out).
- No LLM-generated commit messages; no configurable message.
- No parallelism across projects; no YAML parser dependency; no change to the slug/normalizer/budget/dedupe logic.
- No new limit config surface (125-byte default unchanged).

**Implementation checklist:**
- Add discover_projects(root) (os.walk + prune list; two-signal backlog-root test; regex-read project_name) and a Project dataclass (repo_root, name, backlog_roots); group by git_repo_root(), skip non-git roots with a warning.
- Add git_commit(repo_root, paths, message, no_verify) over run_git, pathspec-scoped to the exact renamed paths.
- Rework main into a per-project loop: collect_files/plan_renames per project -> apply (tracked git mv; untracked plain_rename + NOTICE, uncommitted) -> one hook-respecting (or --no-verify) commit of the tracked renames.
- Add --no-verify; widen --path help; extend the summary with the project tallies; keep exit 1 on any error.
- Extend the pytest file: discovery over a temp tree with decoys, monorepo grouping, pathspec isolation, --no-verify blocked-then-committed, untracked-only, failure isolation.
- Run `uv run pytest` + `uv run ruff check .`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 discover_projects(root) finds every backlog root under --path (dir with config.yml AND a SCAN_SUBDIRS entry like tasks/), pruning .git/node_modules/.venv/__pycache__/.pytest_cache/dist/build and not descending into a found backlog root; a decoy config.yml with no tasks/ and a backlog root outside git are not treated as committable projects
- [x] #2 Backlog roots are grouped by enclosing git repo; two roots in one repo produce one project committed once; a root in no git repo is skipped with a warning
- [x] #3 --apply performs, per project, the existing renames then a single pathspec-scoped git commit of exactly the old+new tracked-rename paths with the fixed 'chore(backlog): shorten N over-limit filename(s) for ecryptfs sync' message; a pre-existing staged unrelated change in that repo is NOT included in the commit
- [x] #4 Untracked over-limit files are renamed with the existing NOTICE and are not committed; a project whose only over-limit files are untracked produces no commit
- [x] #5 Commits respect git hooks by default (a failing hook is reported and that project is skipped without committing); --no-verify bypasses hooks and the commit lands
- [x] #6 A rename or commit failure in one project is reported and the sweep continues; the run exits 1 if any project errored, else 0
- [x] #7 Default dry-run prints per-project grouping, the old->new rows, and a 'Would commit N rename(s) in <name> [<repo_root>]' line and changes nothing; --path backlog still behaves as the single-project case; the summary adds projects=<n> committed=<n> project-errors=<n>
- [x] #8 uv run pytest and uv run ruff check . pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: extend scripts/shorten-backlog-filenames.py in place with a discover -> group -> per-project loop around the existing per-backlog-root machinery. (1) PRUNE_DIRS + is_backlog_root() (two-signal: config.yml AND >=1 SCAN_SUBDIRS entry) + find_backlog_roots() (os.walk top-down, prune list applied to dirnames, dirnames.clear() at a found root so we never descend into one) + project_name() (regex over config.yml, no YAML dep, falls back to the repo dir name) + discover_projects() returning [Project(repo_root, name, backlog_roots)] grouped by git_repo_root(); a root in no git repo is warned and skipped, so it never becomes a committable project. (2) git_commit(repo_root, paths, message, no_verify) over run_git -- 'git commit -m MSG [--no-verify] -- <old> <new>...'; verified empirically that pathspec mode commits the rename and leaves an unrelated staged change out of the commit and still staged. (3) apply_renames now takes repo_root (not a backlog root -- discovery already resolved it) and RETURNS the list of Renames git staged, so only tracked renames reach the commit; untracked keep the plain_rename + NOTICE path and are never git add-ed. (4) sweep_project(project, opts, *, apply, include_archive, no_verify) -> ProjectResult(counters, committed, failed): header + backlog roots, collect/plan across the project's roots, report rows, then either the dry-run 'Would commit N rename(s) in <name> [<repo_root>]' line (N counted with git_tracked so it is truthful) or apply+commit. (5) main loops projects, merges per-project Counters into the totals via Counters.merge (dataclasses.fields), tracks SweepTally(projects, committed, errors) and exits 1 if any file error or any project errored. (6) --no-verify flag; --path help widened. (7) Tests: _make_repo gains the config.yml backlog init always writes (without it --path backlog is no longer a backlog root, which is the point of the two-signal test), plus new cases for discovery/decoys/pruning, monorepo grouping, non-git skip, pathspec isolation, hook-blocked then --no-verify, untracked-only, failure isolation, and the summary tallies. Gates: uv run pytest + uv run ruff check .

Commit: `44b79f1` - task-236: sweep every project's backlog and commit each one separately

Commit: `61e909d` - task-236: pin the project-error tally for a rename-only failure

Implemented. scripts/shorten-backlog-filenames.py is now a discover -> group -> per-project sweep wrapped around the unchanged slug/normalizer/budget/dedupe machinery. Discovery: find_backlog_roots() walks --path top-down, prunes .git/node_modules/.venv/__pycache__/.pytest_cache/dist/build, applies the two-signal backlog-root test (config.yml AND >=1 SCAN_SUBDIRS entry) and does NOT descend into a root it found (a backlog holds artifacts, not projects -- its archive/ carries the same directory names a nested project would). discover_projects() resolves each root through the existing git_repo_root() and groups by repository top-level, so a monorepo's several backlogs are ONE project taking ONE commit; a root in no repository is warned about and dropped rather than renamed without version control. project_name comes from a regex over config.yml (no YAML dependency -- PEP 723 stays stdlib-only) and falls back to the repository directory name. Commit: new git_commit() over run_git runs 'commit [--no-verify] -m <fixed message> -- <old> <new>...'; pathspec form was verified empirically before it was built on, and it commits the rename while leaving an operator's pre-existing staged change out of the commit and still staged. apply_renames() now takes the repository top-level (discovery already resolved it, so its old git_repo_root failure branch moved there) and RETURNS the renames git staged, which is what makes 'only tracked files join the commit' structural rather than a rule to remember -- untracked files keep the plain_rename + NOTICE path and are never git add-ed. sweep_project() prints the project header and its backlog roots, reports the old -> new rows, and either prints 'Would commit N rename(s) in <name> [<repo_root>]' (N counted with git_tracked so the dry run does not promise to commit an untracked file) or applies and commits. Failure isolation is at three levels: a failed rename keeps the file counted in errors, a refused commit is reported and that project is skipped, and main wraps each project in (OSError, ValueError) so one unreadable or exotically-symlinked repository costs that project and not the fleet; the run exits 1 if any file errored or any project errored. Summary gained 'projects=<n> committed=<n> project-errors=<n>'. DECISION: hooks are respected by default and --no-verify is opt-in -- another Ralph project's commit-prefix-guard blocking this message on master is a real answer, not an obstacle to route around. Tests: the fixture builder now writes the config.yml backlog init always writes (without it --path backlog is no longer a backlog root, which is exactly the point of the two-signal test), and 24 new tests cover discovery/decoys/the whole prune list, monorepo grouping and its single commit, the non-git skip warning, pathspec isolation from a staged change, untracked-stays-out-of-the-commit, hook-blocked-then---no-verify, blocked/rename/unexpected-exception isolation, and the dry-run project lines and tallies. test_apply_output_passes_the_filename_length_guard was rewritten to install the repo's real filename-length-guard.sh as the pre-commit hook (with a marker file proving it ran) instead of invoking it by hand -- stronger than what it replaced, since the commit now has to clear the real guard. Every behavioural assertion was mutation-checked: 13 mutations, all killed. Gates: uv run pytest 491 passed (468 on master + 23 net new), uv run ruff check . clean. task-reviewer verdict APPROVED, with one non-blocking finding (project-errors was unpinned for a rename-only failure -- fixed on the branch in 61e909d and the mutation that survived the review is now killed) and two observations recorded rather than changed: the pathspec commit is per-path not per-hunk, so an uncommitted edit to a file that is itself being renamed rides along (now stated in the git_commit docstring), and a backlog whose config.yml is missing yields projects=0 with a warning and exit 0.
<!-- SECTION:NOTES:END -->
