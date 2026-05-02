---
id: TASK-87
title: 'Consolidate hooks: scripts only, settings.json as wiring index'
status: To Do
assignee: []
created_date: '2026-05-02 06:33'
labels:
  - hook
  - refactor
  - cleanup
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Settings.json currently mixes inline bash blobs in PreToolUse hook entries with references to dedicated shell scripts in .claude/hooks/. Many inline blobs duplicate logic that already exists as scripts (commit-msg-guard.sh, naming-guard.sh, notes-guard.sh, commit-prefix-guard.sh, master-branch-guard.sh). Some scripts may be unwired (e.g. task-file-guard.sh). The PostToolUse task-validator.sh is too large to inline anyway, so a unified rule is needed.

## Decision

Single approach: scripts only. Settings.json holds wiring (matcher, if:, command: path), never logic.

## Conventions

1. Every hook lives at .claude/hooks/<name>.sh. Settings.json never contains an inline bash command — only command: ".claude/hooks/<name>.sh".
2. Naming: <domain>-guard.sh for PreToolUse blockers; <domain>-validator.sh for PostToolUse advisors.
3. One script may be wired by multiple if: clauses when the logic is shared (e.g. naming-guard.sh covers both backlog task create * and git checkout -b *; commit-msg-guard.sh covers both git commit * and gh pr create *).
4. Scripts trust the if: gate — they do not re-grep the command pattern. Parsing tool_input for downstream needs (task ID, branch name) is fine.
5. Standard contract: read stdin (tool input JSON), default exit 0 = allow, emit deny JSON to block (PreToolUse) or print diagnostics / system-reminder to stdout (PostToolUse).
6. Each script begins with a header comment block: name, one-line purpose, trigger (matcher + if:), action type (deny JSON / system-reminder / stdout), input shape.
7. Inline comments only where the WHY is non-obvious (regex quirks, BSD vs GNU, defensive || true after pipelines).
8. Template parity: every change to .claude/settings.json or .claude/hooks/ is mirrored in skills/ralph-init/templates/.claude/ in the same commit.

## Out of scope

- Behavior changes to any guard (commit trailer rules, ASCII checks, --notes block, master-branch block, task validator) — pure refactor.
- Renaming existing scripts unless they no longer fit the <domain>-guard.sh / <domain>-validator.sh convention.
- TASK-86 (regex bugs in task-validator.sh) — independent fix.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every inline command: bash blob in .claude/settings.json is replaced with a path to a script in .claude/hooks/
- [ ] #2 Each replacement reuses an existing script when one matches (commit-msg-guard.sh, commit-prefix-guard.sh, naming-guard.sh, notes-guard.sh, master-branch-guard.sh); new scripts are created only when no match exists
- [ ] #3 Scripts no longer re-grep the command pattern that the if: clause already gates (defensive 'grep -qE ^X\\b || exit 0' lines removed)
- [ ] #4 Each hook script in .claude/hooks/ begins with the standard header comment block (name, purpose, trigger, action, input)
- [ ] #5 Any script in .claude/hooks/ not referenced from .claude/settings.json is deleted
- [ ] #6 skills/ralph-init/templates/.claude/settings.json mirrors the project .claude/settings.json hooks section byte-for-byte (modulo path differences if any)
- [ ] #7 skills/ralph-init/templates/.claude/hooks/ mirrors .claude/hooks/ (same files, same headers)
- [ ] #8 Smoke test: git commit -m with a Co-Authored-By trailer is denied with the existing forbidden-trailer message
- [ ] #9 Smoke test: backlog task edit N --notes 'x' is denied by notes-guard.sh; --append-notes 'x' is allowed
- [ ] #10 Smoke test: git checkout -b task-99-тест is denied by naming-guard.sh; ASCII branch name is allowed
- [ ] #11 Smoke test: backlog task edit N --append-notes 'x' triggers task-validator.sh PostToolUse output
- [ ] #12 Smoke test: Edit tool on a non-.claude/ path while on master is denied; the same Edit on a task-* branch is allowed
<!-- AC:END -->
