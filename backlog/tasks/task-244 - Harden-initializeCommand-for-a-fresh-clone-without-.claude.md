---
id: TASK-244
title: Harden initializeCommand for a fresh clone without .claude
status: Done
assignee: []
created_date: '2026-09-27 12:58'
updated_date: '2026-09-27 13:17'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Both the live `.devcontainer/devcontainer.json` and its R11 mirror `plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json` carry this initializeCommand (line ~93 in each):

```json
"initializeCommand": "sh -c '[ -s .claude/settings.local.json ] || echo {} > .claude/settings.local.json'",
```

If the `.claude` directory does not exist, the redirect fails, `sh -c` exits non-zero, and the devcontainer CLI **aborts container creation**. A fresh clone of any ralph-init project whose `.claude` directory is gitignored or otherwise absent therefore cannot start its devcontainer at all.

Proposed fix — create the directory first, keep the `[ -s ]` idempotence that leaves a real host file alone:

```json
"initializeCommand": "sh -c 'mkdir -p .claude && { [ -s .claude/settings.local.json ] || echo {} > .claude/settings.local.json; }'",
```

Discovered while verifying TASK-242 on the host: the break was only avoided because the throwaway scaffold created `.claude` explicitly before running `devcontainer up`.

## Notes for the implementer

- R11 parity applies: live and template must stay byte-identical. `tests/unit/template-parity.bats` pins the pair as an exact mirror.
- `tests/unit/devcontainer-claude-share.bats` already has a test named "initializeCommand seeds the host settings file when missing or empty" (asserting the value contains `.claude/settings.local.json` and `-s `). Extend that test rather than adding a new file.
- ralph-init SKILL.md must be updated in BOTH Init (Step 3.x) and Upgrade Mode (U1-U5) — existing projects only receive this through `ralph-init upgrade`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The live .devcontainer/devcontainer.json initializeCommand creates the .claude directory before the redirect (its value contains mkdir -p .claude)
- [x] #2 The ralph-init template devcontainer.json carries the identical initializeCommand, and the template-parity exact-pair test still passes
- [x] #3 The [ -s ] idempotence is preserved: the command still tests [ -s .claude/settings.local.json ] so an existing non-empty host file is left untouched
- [x] #4 Running the new initializeCommand in a directory that has no .claude exits 0 and leaves .claude/settings.local.json containing {}
- [x] #5 devcontainer-claude-share.bats asserts the directory creation, and that assertion fails against the pre-fix command
- [x] #6 ralph-init SKILL.md documents the change in both Init (Step 3.x) and Upgrade Mode (U1-U5)
- [x] #7 LC_ALL=C bats tests/unit and uv run pytest pass with no new failures
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: prepend mkdir -p .claude (grouping the [ -s ] || echo in braces) in live + template devcontainer.json and their comment; extend the existing bats keyword test with a mkdir assertion and add a behavioral test running the command in a dir without .claude; document in ralph-init SKILL.md 3.6 and U4.

Commit: `ae5dad7` - task-244: create .claude before seeding settings.local.json in initializeCommand

Implemented: initializeCommand now runs mkdir -p .claude before the [ -s ] || echo {} seed (brace-grouped) in live + template devcontainer.json (byte-identical). bats: keyword test asserts mkdir -p .claude; new behavioral test runs the command from both files in a dir without .claude (exit 0, file == {}). Both fail against the pre-fix live file. SKILL.md 3.6 + U4 documented. task-reviewer APPROVED. Suites: bats unit 153/154 (sole failure 'R11: settings.local.json keeps the template's JSON shape' is pre-existing on master), pytest 498 passed, ruff clean.

Commit: `0b206fa` - task-244: bump plugin version to 0.6.5 (patch)
<!-- SECTION:NOTES:END -->
