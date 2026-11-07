---
id: TASK-329
title: >-
  master-provenance.sh supports a Ralph project nested in a subdirectory of its
  git repo
status: To Do
assignee: []
created_date: '2026-11-07T14:13:00Z'
updated_date: '2026-11-07T15:05:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

`plugins/ralph/scripts/master-provenance.sh`, R-INFRA-6's checker, assumes the Ralph project is the root of its git repo. A project can also live in a subdirectory of a larger repo, for example `.config/agterm/` inside the owner's `~/Private/Profile` dotfiles repo. The checker is unusable there:

1. **Config.** It reads `.claude/task-reviewer.conf` at `git rev-parse --show-toplevel`. The task-reviewer agent reads `${CLAUDE_PROJECT_DIR}/.claude/task-reviewer.conf`, the project's own file, so `master_provenance_since` and `master_bookkeeping_paths` set in the project never reach the script.
2. **Task notes.** It reads them from `backlog/tasks/` at the repo root and fails for every task with `fatal: path '.config/agterm/backlog/tasks/task-1 - ….md' exists, but not 'backlog/tasks/task-1 - ….md'`. So no `Review: APPROVED <sha>` note is ever found.
3. **Task files.** A `task-N: ` commit that changes only `<prefix>backlog/tasks/…` is not recognised as a task-file commit.
4. **Scope.** It judges every first-parent commit of the host repo's master. That includes the owner's direct commits for unrelated tools and other nested projects, which can never pass.

The agterm project's first review under plugin 0.22.2 got 190 FLAG lines, 110 of them for commits under `.config/agterm/`. Its TASK-29 could not merge. agterm now works around this with a project rule (R-PROJ-1 in its `.claude/task-reviewer-rules.md`) that checks R-INFRA-6 by hand. It drops the rule once this lands.

## Scope

In scope:
- **Prefix.** Resolve the project's prefix in its repo: `git rev-parse --show-prefix` from the project root, empty when the project is the repo root.
- **Config.** Read `.claude/task-reviewer.conf` from the project directory, the file the agent reads.
- **Task files and notes.** Use `<prefix>backlog/{tasks,drafts,archive,completed}/` for both, with no `fatal:` lines.
- **Bookkeeping paths.** Treat `master_bookkeeping_paths` as relative to the project.
- **Which commits are judged.** In a nested project, only first-parent master commits that change at least one path under the prefix. The rest are skipped, e.g. printed as `ok <sha> outside the project`.
- **Rule text.** R-INFRA-6 in `task-reviewer-rules.infra.md` says how the checker treats a nested project.

Out of scope:
- `master-branch-guard.sh`, the integrate/shared-backlog flow and the merge-tree equality rule, apart from what the prefix needs.
- Any change for projects at the repo root: their output must stay identical.

## Files

- `plugins/ralph/scripts/master-provenance.sh` (exists) — prefix resolution, config location, task paths, commit scope.
- `tests/python/test_master_provenance.py` (exists) — nested-project fixtures next to the existing root-project cases.
- `plugins/ralph/skills/ralph-init/rules/task-reviewer-rules.infra.md` (exists) — R-INFRA-6 text for nested projects.
- `plugins/ralph/agents/task-reviewer.md` (exists) — read only. It shows where the agent reads the config (`PROJECT_CONF`); change it only if the wording must match.

## Source

Source: /Users/paul/Private/Profile/.config/agterm@916a4fa3b416-dirty
The agterm side lives in `/Users/paul/Private/Profile/.config/agterm/.claude/task-reviewer-rules.md` (R-PROJ-1). It is read-only context: do NOT modify it.

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, build command, or visible behavior — not "works correctly").
3. All dependencies in the task's frontmatter are status=Done.
4. Out-of-scope items are not accidentally pulled in by ambiguous AC.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Run from a project that is a subdirectory of its repo, master-provenance.sh reads that project's .claude/task-reviewer.conf (master_provenance_since, master_bookkeeping_paths) and ignores one at the repo root (pytest fixture)
- [ ] #2 In a nested project a task-N commit that changes only <prefix>backlog/{tasks,drafts,archive,completed}/ is ok as a task-file commit, and a Review: APPROVED <sha> note in <prefix>backlog/tasks/ covers that task's reviewed work, with no 'fatal: path' lines on stderr (pytest)
- [ ] #3 In a nested project a first-parent master commit that changes nothing under the prefix is not flagged (pytest with a direct commit outside the project)
- [ ] #4 In a nested project a commit under the prefix that is neither allowlist, task file nor reviewed work is still flagged (pytest)
- [ ] #5 For a project at the repo root the output is unchanged: the existing tests/python/test_master_provenance.py cases pass without edits
- [ ] #6 R-INFRA-6 in plugins/ralph/skills/ralph-init/rules/task-reviewer-rules.infra.md describes the nested-project behaviour, the script stays bash 3.2 and BSD/GNU portable (R-INFRA-3), and uv run pytest plus uv run ruff check . pass
- [ ] #7 The script takes the project root from CLAUDE_PROJECT_DIR when it is set, else from the working directory, and computes the prefix there; run from a subdirectory of a root project with CLAUDE_PROJECT_DIR set to the repo root, its output is identical to a run from the root (pytest)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Acceptance check on the destination (2026-11-07): yellow, clarified by the owner. All (exists) paths are present, the description matches the code (conf at show-toplevel, line 215; task notes from the root backlog/tasks, line 248), every AC is pass/fail, and there are no dependencies. Clarification: the project root comes from CLAUDE_PROJECT_DIR, the same source the task-reviewer agent uses for PROJECT_CONF, else the working directory (owner's choice A over an explicit --project flag or a bare working directory); added as AC #7. Run after the other host lands TASK-312/313/315, which may touch the integrate side of this checker; this task changes shipped files and needs a version bump.
<!-- SECTION:NOTES:END -->
