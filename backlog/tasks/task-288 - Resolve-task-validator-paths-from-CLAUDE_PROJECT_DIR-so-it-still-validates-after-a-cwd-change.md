---
id: TASK-288
title: >-
  Resolve task-validator paths from CLAUDE_PROJECT_DIR so it still validates
  after a cwd change
status: To Do
assignee: []
created_date: '2026-10-25T16:15:00Z'
labels:
  - feature:ralph-init
dependencies:
  - TASK-280
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

TASK-280 anchored every hook command at "$CLAUDE_PROJECT_DIR", so after a `cd <subdir> && …` the hooks start again. task-validator.sh itself still resolves everything from the session's current directory: it finds the task file with `find backlog/tasks …`, checks dependencies the same way, reads the change with `git diff HEAD -- "backlog/tasks/task-${TASK_ID}"*`, and checks referenced paths with `[[ -e "$path" ]]`. From a subdirectory the find returns nothing and the hook exits 0 with no output, so a `backlog task create` or `backlog task edit` after a cd is silently not validated: no [det] issues and no LLM rubric nudge. TASK-280 put the hook scripts' own logic out of scope; this is that follow-up.

Found by the task-reviewer during a ralph-init 0.14.7 upgrade in a downstream project, and reproduced on the 0.14.7 template:

```bash
T=$(mktemp -d); mkdir -p "$T/backlog/tasks" "$T/sub"
printf '%s\n' '---' 'id: TASK-1' 'title: Sample' 'status: To Do' 'dependencies: [TASK-9]' '---' '' \
  '## Description' '' 'Some text.' '' '## Acceptance Criteria' '- [ ] #1 one' >"$T/backlog/tasks/task-1 - Sample.md"
H=$PWD/plugins/ralph/skills/ralph-init/templates/claude/hooks/task-validator.sh
J='{"tool_input":{"command":"backlog task edit 1 -s \"To Do\""}}'
(cd "$T"     && echo "$J" | CLAUDE_PROJECT_DIR="$T" RALPH_AUTONOMOUS=0 bash "$H")  # root: "[det] ... Dependency TASK-9 not found"
(cd "$T/sub" && echo "$J" | CLAUDE_PROJECT_DIR="$T" RALPH_AUTONOMOUS=0 bash "$H")  # subdir: no output, exit 0
```

(Run it from the ralph repo root, so H is the template's absolute path before the subshells cd away.)

## Scope

In scope:
- task-validator.sh (template and live copy) runs its file lookups, the dependency check, the git diff and the path-existence check from the project root: "$CLAUDE_PROJECT_DIR" when set, otherwise the current directory as today. One early line is enough, for example:

```bash
# Hooks run from the session's cwd, which a `cd <subdir> && …` moves; resolve task paths from the project root.
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
```

- The rubric's "File:" line names the task file so that it resolves from any cwd (absolute path).
- bats cases for the subdirectory runs.

Out of scope:
- The other hooks. master-branch-guard.sh and commit-prefix-guard.sh ask git, which works from any directory inside the repo.
- settings.json hook commands (TASK-280, done).
- The duplicate task ID groups that `backlog task list` reports in this repo (TASK-77, TASK-101, TASK-102, TASK-235).
- Updating downstream projects; they get the change through the ralph-init upgrade, whose managed-file-drift check compares the hook by content.

## Files

- `plugins/ralph/skills/ralph-init/templates/claude/hooks/task-validator.sh` (exists): the fix.
- `.claude/hooks/task-validator.sh` (exists): live copy, kept identical to the template.
- `tests/unit/task-validator.bats` (exists): new subdirectory cases next to the existing root-cwd ones.
- `tests/unit/template-parity.bats` (exists): parity pin, must stay green.

## Source

Source: /Users/paul/Private/Profile/.config/agterm@81fae8c352d4
Observed in that project's TASK-17 review notes (ralph-init upgrade to 0.14.7); its task-validator.sh is byte-identical to the 0.14.7 template. No source design doc.

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
- [ ] #1 A bats case in tests/unit/task-validator.bats runs the template validator from a subdirectory with CLAUDE_PROJECT_DIR set to the project root, on a task depending on a missing TASK-9, and gets the same 'Dependency TASK-9 not found' [det] output as from the root
- [ ] #2 A bats case: from a subdirectory, a backlog task create whose description backticks an existing root-relative path reports no 'does not exist' issue for it, and a missing path is still reported
- [ ] #3 From a subdirectory, the LLM rubric's File: line names the task file by an absolute path that exists
- [ ] #4 With CLAUDE_PROJECT_DIR unset, the existing tests/unit/task-validator.bats cases pass unchanged
- [ ] #5 .claude/hooks/task-validator.sh is identical to the template, and tests/unit/template-parity.bats passes
- [ ] #6 The reproduction in the description, run on the macOS host after the fix, prints the [det] dependency issue from the subdirectory too; the output is recorded in the task notes
- [ ] #7 uv run pytest passes, uv run ruff check . is clean, and LC_ALL=C bats tests/unit has no failures
<!-- AC:END -->
