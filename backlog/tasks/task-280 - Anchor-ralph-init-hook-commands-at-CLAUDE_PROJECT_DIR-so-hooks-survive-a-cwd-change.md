---
id: TASK-280
title: >-
  Anchor ralph-init hook commands at CLAUDE_PROJECT_DIR so hooks survive a cwd
  change
status: Done
assignee: []
created_date: '2026-10-18 08:40'
updated_date: '2026-10-18 09:37'
labels:
  - 'feature:ralph-init'
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

ralph-init's `templates/claude/settings.json` registers every hook by a relative path (`.claude/hooks/<name>.sh`). Claude Code runs the hook command from the session's current directory, and that directory moves whenever a Bash call does `cd <subdir> && …`. From then on every Bash/Edit/Write call prints `PreToolUse:Bash hook error — /bin/sh: .claude/hooks/commit-msg-guard.sh: No such file or directory` (one line per registered hook). Claude Code treats these errors as non-blocking, so the guards (commit-msg, commit-prefix, naming, notes, master-branch, task-validator) are silently skipped and enforce nothing. This was observed on 2026-10-18 in a Ralph-managed project after one `cd presentations/<deck> && grep …`. Claude Code's documented fix is to anchor hook commands at the project root: `"$CLAUDE_PROJECT_DIR"/.claude/hooks/<name>.sh`.

## Scope

In scope:
- Rewrite every `command` in `plugins/ralph/skills/ralph-init/templates/claude/settings.json` to `"$CLAUDE_PROJECT_DIR"/.claude/hooks/<name>.sh`, with the variable in double quotes so paths with spaces work.
- Apply the same change to this repo's live `.claude/settings.json`. `tests/unit/template-parity.bats` pins the two files as exact copies.
- Add a regression test that fails on any relative hook command and on any command naming a script that does not exist in `templates/claude/hooks/`.
- In the ralph-init Upgrade Mode section, add one note: projects whose `.claude/settings.json` carries extra hook entries of their own (the upgrade shows a diff for this file) should convert those entries to the same `"$CLAUDE_PROJECT_DIR"` form.

Out of scope:
- The hook scripts' own logic (`templates/claude/hooks/*.sh`).
- `settings.local.json` permission rules.
- Updating downstream projects. They pick the change up through `ralph-init` upgrade, where `managed-file-drift.sh` already compares `.claude/settings.json` by exact content.
- The stale AGENTS.md line claiming hook logic is inlined in settings.json.

## Files

- `plugins/ralph/skills/ralph-init/templates/claude/settings.json` (exists): the hook command paths.
- `.claude/settings.json` (exists): live copy, kept exact per template-parity.
- `tests/unit/template-parity.bats` (exists): parity pin, must stay green.
- `tests/unit/` (exists): new bats test for the hook-command form, file name at the implementer's choice.
- `plugins/ralph/skills/ralph-init/SKILL.md` (exists): Upgrade Mode note.
- `plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh` (exists): read-only check that an old relative-path settings.json reports `outdated`.

Reproduction (any Ralph-managed project, interactive Claude Code session at the project root):

```bash
cd plugins && ls          # moves the session cwd into a subdirectory
git status                # next Bash call: hook errors "No such file or directory", guards skipped
```

Target form of one entry:

```json
{
  "type": "command",
  "if": "Bash(git commit *)",
  "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/commit-msg-guard.sh"
}
```

## Source

Source: /Users/paul/Private/Alfa/Projects/equation/services@7495e40e697f-dirty
Observed in the source project's `.claude/settings.json` (identical hook entries to the ralph-init template plus one project-specific entry). No source design doc.

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
- [x] #1 jq -r '.. | .command? // empty' over plugins/ralph/skills/ralph-init/templates/claude/settings.json and .claude/settings.json prints only commands of the form "$CLAUDE_PROJECT_DIR"/.claude/hooks/<name>.sh — none starts with .claude/
- [x] #2 A new bats test under tests/unit/ fails when any hook command in the template is relative or names a script missing from templates/claude/hooks/, and passes on the fixed template
- [x] #3 Each fixed command string, run as sh -c '<command>' from a subdirectory (cd plugins) with CLAUDE_PROJECT_DIR set to the repo root and a sample hook JSON on stdin, exits with a code other than 127; the per-hook exit codes are recorded in the task notes
- [x] #4 The same sh -c check inside the devcontainer with CLAUDE_PROJECT_DIR=/workspace exits with a code other than 127; result recorded in the task notes
- [x] #5 managed-file-drift.sh run against a scratch project whose .claude/settings.json has the old relative paths reports .claude/settings.json as outdated (output recorded in the task notes)
- [x] #6 ralph-init SKILL.md Upgrade Mode tells projects with their own extra hook entries in .claude/settings.json to convert them to the "$CLAUDE_PROJECT_DIR" form
- [x] #7 npm test and uv run pytest pass; uv run ruff check . is clean
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: handoff checklist green (all Files paths exist, no deps, ACs are commands). Rewrite every hook command in templates/claude/settings.json and live .claude/settings.json to "$CLAUDE_PROJECT_DIR"/.claude/hooks/<name>.sh via sed; add tests/unit/hook-command-paths.bats (jq over the template: every command matches the anchored form and names an existing templates/claude/hooks script; negative cases on a mutated copy); add an Upgrade Mode U3 note for custom hook entries; run sh -c checks from plugins/ and managed-file-drift.sh on a scratch project with the old file.

Verification (devcontainer f18c39e599b9, repo root /workspace, so AC3 and AC4 ran in the same environment; no macOS host run from here):
- AC1: jq over both settings files prints only "$CLAUDE_PROJECT_DIR"/.claude/hooks/<name>.sh (13 commands each, 6 distinct scripts); none starts with .claude/.
- AC2: tests/unit/hook-command-paths.bats, 5/5 pass; negative cases (relative, unquoted variable, missing script) fail check_commands on mutated copies.
- AC3/AC4: from plugins/ with CLAUDE_PROJECT_DIR=/workspace and a sample Bash hook JSON on stdin: commit-msg-guard 0, commit-prefix-guard 0, master-branch-guard 0, naming-guard 0, notes-guard 0, task-validator 0. Old relative .claude/hooks/notes-guard.sh from plugins/ gives 127. Extra: project dir with a space in its path, rc 0.
- AC5: scratch project with master's relative-path settings.json: managed-file-drift.sh check prints ".claude/settings.json: outdated"; with the fixed template the line disappears.
- AC6: U3 settings.json bullet now tells projects to convert their own hook entries to the anchored form.
- AC7: uv run pytest 901 passed, 3 skipped; ruff clean. npm test: 9 failures, all environmental and unrelated to the diff. 8 reproduce identically on a clean master worktree (bump-version nudge x2, filename-length-guard 125-byte, task-reviewer-rules-loading x5, R-CORE-5 scan). The 9th, R11 settings.local.json shape, reads the gitignored per-developer file, which is absent in the worktree and is the container's sandbox-off copy here. No failure involves settings.json or the new test.

Commit: `014c06b` - task-280: anchor hook commands at "$CLAUDE_PROJECT_DIR" so hooks survive a cwd change

Correction to the AC7 note: the master baseline is 8 failures = bump-version nudge x2, filename-length-guard 125-byte x1, task-reviewer-rules-loading x4, R-CORE-5 scan x1 (not loader x5). Review: ralph:task-reviewer APPROVED, 0 blocking, 1 minor. The minor finding is that npm test does not literally pass in the container, so AC7 rests on the master-baseline comparison; a host npm test run was not done.

Commit: `c5fa5db` - task-280: bump plugin version to 0.14.4 (patch)

Host re-check (macOS /bin/sh, after merge in 0.14.4): from plugins/ with CLAUDE_PROJECT_DIR=/Users/paul/Private/Projects/ai/ralph and a sample Bash hook JSON on stdin, every distinct command in .claude/settings.json exits 0 — "$CLAUDE_PROJECT_DIR"/.claude/hooks/{commit-msg-guard,commit-prefix-guard,master-branch-guard,naming-guard,notes-guard,task-validator}.sh; control: the old relative .claude/hooks/commit-msg-guard.sh from plugins/ exits 127. Host gates on master 0.14.7: ruff clean, pytest 912 passed/4 skipped, LC_ALL=C bats tests/unit 169 ok/0 not ok.
<!-- SECTION:NOTES:END -->
