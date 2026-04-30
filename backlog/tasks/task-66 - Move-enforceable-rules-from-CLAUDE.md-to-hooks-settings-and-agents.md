---
id: TASK-66
title: 'Move enforceable rules from CLAUDE.md to hooks, settings, and agents'
status: To Do
assignee: []
created_date: '2026-04-30 11:30'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Move enforceable rules out of CLAUDE.md into Claude Code hooks, settings, and a dedicated review subagent. Goal: shrink CLAUDE.md from ~138 lines to ~55-65 lines by keeping only judgment/workflow content, while moving pattern-matching enforcement to PreToolUse hooks that block bad commands at execution time with actionable error messages.

## Scope

**5 PreToolUse hooks added to .claude/settings.json:**

1. **Commit message guard** — match `git commit` and `gh pr create`. Block if message contains: `Co-Authored-By` (case-insensitive, also catches `Co-authored-by`), `Generated with Claude Code`, or a `## Test plan` heading. Error: `BLOCKED: forbidden trailer/heading. Remove Co-Authored-By, Generated-with, and Test plan sections.`

2. **--notes guard** — match `backlog task edit` containing ` --notes ` or ` --notes=` (NOT `--append-notes`). Error: `BLOCKED: --notes overwrites the Notes section and destroys commit hashes. Use --append-notes instead.`

3. **Task file edit guard** — match Edit/Write tool calls where path matches `backlog/tasks/*.md`. Error: `BLOCKED: do not edit task files directly. Use backlog task edit (run \`backlog task edit --help\` for syntax).`

4. **Master-branch edit guard** — match Edit/Write when current git branch is `master`. Allow if path matches `.claude/**` or is exactly `.gitignore`. Otherwise block. Error: `BLOCKED: no active task branch. Create a backlog task and \`git checkout -b task-<id>-<desc> master\` first.`

5. **Naming guard** — two sub-hooks:
   - `backlog task create \"<title>\"`: extract first quoted positional arg, block if it contains non-ASCII letters. Must NOT scan -d/--description/--ac flag values.
   - `git checkout -b <name>`: block if branch name contains non-ASCII.
   Error: `BLOCKED: title/branch must be ASCII English (filenames are derived from titles). Put translations in -d or --ac.`

6. **Commit prefix guard** — match `git commit` when on a `task-*` branch. Block if message lacks `task-<id>: ` prefix (where `<id>` matches the branch's task ID). Allow merge commits (`Merge branch ...`). Error: `BLOCKED: commit message on task-<id> branch must start with \`task-<id>: \`.`

**New subagent: .claude/agents/task-reviewer.md**

Move the 8-item code review checklist from CLAUDE.md into this agent's system prompt:
1. Acceptance criteria met
2. Functionality correct, edge cases handled
3. No bugs, proper error handling
4. No security issues (injection, XSS, secrets)
5. Consistent code style
6. Test coverage for new functionality
7. No debug code or commented-out code
8. No unintended changes to other files

Agent should run `git diff master..HEAD` and `backlog task <id> --plain` itself.

**CLAUDE.md rewrite — target structure (~55-65 lines):**

1. **Autonomous Mode** (merged from current top block + Ralph Loop section, ~12 lines). Covers: one-task-per-iteration rule, task selection (named in prompt vs lowest-ID To Do), Task Summary format block, COMPLETE promise rule.
2. **Task Lifecycle** (compressed to 5-6 steps from current 14): gate → plan → implement → review → mark done → merge. Drop GATE repetition and CLI examples.
3. **Backlog CLI** — one line: `Use \`backlog\` CLI for all task ops; run \`backlog task edit --help\` for syntax.`
4. **Project Knowledge Sources** — kept as-is.
5. **Code Quality** — kept as-is (no hook).
6. **Commit & PR Brevity** — keep ONLY the judgment line: `Commit messages should describe what the code does, not its history or evolution.` Other lines moved to hook 1.
7. **Scope** — 2 lines: `Every change needs a backlog task and a \`task-*\` branch — the master-branch hook enforces this. One task per iteration, one branch per task.`
8. **Knowledge Sharing** — kept as-is.
9. **Code Review** — one line: `After tests pass, spawn the \`task-reviewer\` agent on \`git diff master..HEAD\`.`
10. **Browser Testing** — kept as-is.
11. **Project-Specific** — kept as-is.

**Sections deleted entirely from CLAUDE.md:**
- Git Hooks block (lines 40-43): `--notes` rule moved to hook 2; post-commit hash mechanic is internal — Claude doesn't need to know.
- Naming Convention section (lines 88-91): moved to hook 5.
- Code Review checklist body (lines 109-117): moved to task-reviewer agent.
- Backlog CLI Reference command list (lines 47-52): replaced with one-liner.

## Implementation notes

- Hook scripts can live in `.claude/hooks/` (new dir). Each hook is a small bash script reading the tool input from stdin (JSON) and exiting non-zero with stderr message to block.
- `.claude/settings.json` (NOT `.claude/settings.local.json`) — these hooks are project-wide rules, not user-specific overrides.
- After implementation, run a smoke test: try a forbidden commit, verify it blocks; try a valid commit, verify it passes.
- The ralph-init skill's CLAUDE.md template should also be updated to match (separate sub-task or include here).

## Risks

- Hook regex bugs could block legitimate commands. Each hook needs a unit test or at least a manual verification list.
- The master-branch edit guard with allowlist must correctly identify the current branch via `git rev-parse --abbrev-ref HEAD` and handle detached HEAD state gracefully.
- Naming hook for `backlog task create` must parse shell quoting correctly to avoid scanning -d/--ac values.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All 6 PreToolUse hooks defined in .claude/settings.json with paths to scripts in .claude/hooks/
- [ ] #2 Each hook script blocks the documented forbidden case with the documented error message
- [ ] #3 Each hook script allows the documented permitted case (e.g., --append-notes, ASCII titles, .claude/** edits on master)
- [ ] #4 .claude/agents/task-reviewer.md created with the 8-item checklist and self-runs git diff + backlog task <id>
- [ ] #5 CLAUDE.md rewritten to target structure (sections 1-11 above), measurable: line count in [55, 75] range
- [ ] #6 CLAUDE.md sections deleted: Git Hooks block, Naming Convention, Code Review checklist body, Backlog CLI command list
- [ ] #7 Smoke test: attempt forbidden commit (with Co-Authored-By trailer) — blocks with hook 1 error; valid commit succeeds
- [ ] #8 Smoke test: attempt backlog task edit ... --notes 'foo' — blocks with hook 2 error; --append-notes succeeds
- [ ] #9 Smoke test: attempt Edit on backlog/tasks/task-1*.md — blocks with hook 3 error
- [ ] #10 Smoke test: on master branch, attempt Edit on README.md — blocks with hook 4; attempt Edit on .claude/settings.json — succeeds
- [ ] #11 Smoke test: backlog task create 'Привет' — blocks with hook 5; backlog task create 'Hello' -d 'Привет описание' — succeeds
- [ ] #12 Smoke test: on task-99 branch, git commit -m 'foo' — blocks with hook 6; git commit -m 'task-99: foo' — succeeds; git commit -m 'Merge branch x' — succeeds
- [ ] #13 ralph-init skill template CLAUDE.md and template .claude/settings.json updated to match (so new projects bootstrap with the same hooks and shorter CLAUDE.md)
<!-- AC:END -->
