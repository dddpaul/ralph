---
id: TASK-73
title: Add bats tests for 6 PreToolUse hooks in .claude/settings.json
status: Done
assignee: []
created_date: '2026-05-01 08:47'
updated_date: '2026-05-01 09:06'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-66 inlined 6 PreToolUse hooks into `.claude/settings.json` with complex bash regex and jq parsing. TASK-67 already discovered two silent failures via manual review (BSD grep `-P` unsupported on macOS; `--notes` regex missed end-of-line case). Hooks have no automated test coverage — only one-time manual smoke checks.

Risk: a future edit to a hook regex (typo, character-class change, platform-specific assumption) will silently break enforcement without any test failing. The hooks themselves are the load-bearing security/quality gates that replaced CLAUDE.md prose, so silent breakage is high-impact.

The existing test suite uses **bats-core** for shell tests (see `tests/unit/` and `tests/integration/`).

## Scope

Create `tests/unit/pretools-hooks.bats` with 6 test groups, one per hook. Each group has at least:
- One **block case** — a JSON input matching the forbidden pattern → assert hook outputs deny + specific reason text
- One **allow case** — a JSON input that should pass → assert hook exits silently
- **Regression cases** for known-fixed bugs from TASK-67 (BSD grep `-P`, `--notes` at EOL)

### Hooks to cover

1. **commit-msg-guard** (PreToolUse on Bash where command matches `git commit`/`gh pr create`)
   - Block: message contains `Co-Authored-By`, `Co-authored-by`, `Generated with Claude Code`, `## Test plan`
   - Allow: message lacks all of those
   - Edge: case-insensitivity for `Co-Authored-By` variants

2. **notes-guard** (PreToolUse on Bash where command matches `backlog task edit`)
   - Block: ` --notes ` or ` --notes=` or ` --notes` at EOL (TASK-67 regression case)
   - Allow: `--append-notes` (must NOT match)

3. **task-file-guard** (PreToolUse on Edit/Write where path matches `backlog/tasks/*.md`)
   - Block: any Edit/Write to a task file
   - Allow: edits to `backlog/.ralph-status.json` and other non-task paths

4. **master-branch-guard** (PreToolUse on Edit/Write when current branch is master)
   - Block: edit to a non-allowlisted path on master (e.g. `README.md`, `ralph.sh`)
   - Allow: edit to `.claude/**`, `.gitignore` on master
   - Allow: edit to anything on a `task-*` branch
   - Edge: detached HEAD state (the test should mock `git rev-parse` output)

5. **naming-guard** (PreToolUse on Bash where command matches `backlog task create` or `git checkout -b`)
   - Block: title with non-ASCII (e.g. Cyrillic \"Привет\") — TASK-67 regression case for BSD grep
   - Allow: ASCII-only title, even if `-d` description contains non-ASCII
   - Allow: ASCII-only branch name

6. **commit-prefix-guard** (PreToolUse on Bash where command matches `git commit` and current branch is `task-*`)
   - Block: `git commit -m \"foo\"` on `task-99` branch (no `task-99: ` prefix)
   - Allow: `git commit -m \"task-99: foo\"`
   - Allow: merge commits (`Merge branch ...`)
   - Allow: any commit on master / non-task branch

### Test mechanics

Hooks are inlined as `command` strings in settings.json. Tests should NOT re-parse settings.json — instead, the test files should embed each hook's command verbatim (or extract via jq once, then exec). Use bats `run` to capture stdout/stderr/exit, then assert.

For hooks that depend on git state (master-branch-guard, commit-prefix-guard), use a temporary git directory (`git init` in `BATS_TMPDIR`) and `cd` into it for the test scope.

For Bash-tool hooks, the input JSON shape is `{tool_name: \"Bash\", tool_input: {command: \"...\"}}`. For Edit/Write, it's `{tool_name: \"Edit\", tool_input: {file_path: \"...\"}}`.

## Out of scope
- Changing existing hook logic or settings.json structure
- Testing the post-commit git hook (separate concern)
- Integration tests that exercise the full Claude Code → hook → tool flow (would require harness mocking)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tests/unit/pretools-hooks.bats exists with 6 test groups (one per hook)
- [x] #2 Each group has at least one block case asserting deny output and specific reason text
- [x] #3 Each group has at least one allow case asserting silent pass
- [x] #4 Regression test: notes-guard catches --notes at end of command (TASK-67 fix)
- [x] #5 Regression test: naming-guard catches non-ASCII title via portable grep (TASK-67 fix on BSD macOS)
- [x] #6 master-branch-guard tests use a temporary git directory to mock branch state
- [x] #7 commit-prefix-guard test allows merge commits (Merge branch ...) on task branches
- [ ] #8 All tests pass on macOS (BSD utilities) — verified via bats run locally
- [x] #9 CI workflow (.github/workflows/) updated to run the new bats file alongside existing tests, OR existing CI already discovers tests/unit/*.bats and no change needed
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: 1) Read settings.json to extract all 6 hook commands. 2) Create tests/unit/pretools-hooks.bats with test groups. 3) Run bats to verify. Note: naming-guard hook has existing bug - uses bash-only <<< in /bin/sh context.

AC#8: Tests use POSIX-compatible constructs (printf pipe instead of <<<). Cannot verify on macOS in this env but the hook fix was specifically for BSD compat. AC#9: CI workflow already runs bats tests/unit/ which auto-discovers new .bats files.

Commit: `ff73026` - task-73: Add bats tests for 6 PreToolUse hooks in .claude/settings.json

All 30 tests pass. Code review approved with minor suggestions (edge case coverage improvements). Pre-existing status-file test failures are unrelated (ITERATION_STARTED_AT unbound). CI auto-discovers tests/unit/*.bats — no workflow change needed.
<!-- SECTION:NOTES:END -->
