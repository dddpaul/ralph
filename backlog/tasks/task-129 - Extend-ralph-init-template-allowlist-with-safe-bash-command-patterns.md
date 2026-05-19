---
id: TASK-129
title: Extend ralph-init template allowlist with safe bash command patterns
status: Done
assignee: []
created_date: '2026-05-19 08:44'
updated_date: '2026-05-19 12:26'
labels: []
dependencies:
  - TASK-127
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Split from TASK-127 (Section C). Ralph happy path uses bash commands not in the template allowlist — each triggers a permission prompt. List was empirically collected during a session running ralph in `/Users/paul/Private/Alfa/Projects/enterprise`.

## Safe to wildcard (`:*`)

These are read-only, scoped, or already constrained by their subcommand surface:

```
Bash(backlog task view:*)
Bash(backlog task archive:*)
Bash(backlog config:*)
Bash(backlog doc view:*)
Bash(backlog doc list:*)
Bash(git checkout:*)
Bash(git merge:*)
Bash(git mv:*)
Bash(git rm:*)
Bash(mkdir:*)
Bash(chmod:*)
Bash(tee:*)
Bash(jq:*)
Bash(ps:*)
Bash(tail:*)
Bash(head:*)
Bash(wc:*)
```

## CRITICAL — do NOT wildcard destructive commands

User constraint: `Bash(rm:*)`, `Bash(cp:*)`, `Bash(mv:*)`, `Bash(rmdir:*)`, `Bash(kill:*)` MUST NOT be added with `:*`. They're too dangerous — `rm -rf /`, `mv ~/.ssh /tmp`, `kill 1` are one keystroke away once wildcarded. Either narrow to specific safe forms (e.g. `Bash(rm $TMPDIR/*:*)`, `Bash(kill -TERM `pgrep -f ralph.sh`)`) in a follow-up, or omit entirely and let Claude prompt on each rare use.

## Out of scope

- Defining narrow forms for the destructive commands — that's a separate follow-up requiring careful per-pattern analysis.
- Skill / deferred-tool rules — covered by sibling task 128.
- pptx helpers — covered by sibling task 127d.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 templates/claude/settings.local.json adds exactly these 17 safe-wildcard entries: Bash(backlog task view:*), Bash(backlog task archive:*), Bash(backlog config:*), Bash(backlog doc view:*), Bash(backlog doc list:*), Bash(git checkout:*), Bash(git merge:*), Bash(git mv:*), Bash(git rm:*), Bash(mkdir:*), Bash(chmod:*), Bash(tee:*), Bash(jq:*), Bash(ps:*), Bash(tail:*), Bash(head:*), Bash(wc:*)
- [x] #2 jq -r '.permissions.allow | length' on the template shows count = old count + 17
- [ ] #3 Smoke test on a freshly ralph-init'd project: running a normal Ralph task lifecycle (create branch via git checkout, jq merge during 3.7b, mkdir for scaffolding, git merge to master) does not trigger any permission prompt for the 17 listed safe commands
- [x] #4 templates/claude/settings.local.json does NOT contain any of: Bash(rm:*), Bash(cp:*), Bash(mv:*), Bash(rmdir:*), Bash(kill:*), Bash(bash:*), Bash(sh:*), Bash(zsh:*) — verified by grep -E 'Bash\(rm:|Bash\(cp:|Bash\(mv:|Bash\(rmdir:|Bash\(kill:|Bash\(bash:|Bash\(sh:|Bash\(zsh:' returning no matches. Specific path-narrowed forms like Bash(bash $HOME/.claude/skills/.../script.sh:*) are still allowed because the colon does not immediately follow the shell name.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Add exactly 17 safe-wildcard Bash entries to skills/ralph-init/templates/claude/settings.local.json permissions.allow array, grouped logically with existing families (backlog, git, misc bash). Current count=30 -> target 47. Do NOT add any destructive :* wildcard (rm/cp/mv/rmdir/kill/bash/sh/zsh). Verify via jq length and grep -E guard. Then task-reviewer.

AC#1/#2/#4 verified: jq length=47 (was 30, +17). All 17 entries present (jq index check). Destructive guard grep -E returned no matches. AC#3 (end-to-end smoke test on fresh ralph-init project with full lifecycle, no permission prompts) deferred for manual verification — not automatable in autonomous loop; wiring confirmed via SKILL.md Step 3.7a which copies templates/claude/settings.local.json verbatim to .claude/settings.local.json. Precedent: sibling task-128 deferred its smoke-test AC the same way.

Test hygiene: ran npx bats tests/unit tests/integration. One failure: 'Temp file cleaned up on timeout' (tests/integration/timeout-handling.bats). Confirmed PRE-EXISTING and UNRELATED — ralph.sh and the test file are byte-identical between master and task-129 (git diff master..HEAD empty for both). TASK-129 only modifies skills/ralph-init/templates/claude/settings.local.json (a JSON template with zero ralph.sh runtime interaction). Not fixing here: out of scope, would need its own task/branch per CLAUDE.md Scope rule. Change-relevant checks all pass: JSON valid, count 30->47, 17 entries present, destructive grep guard clean.

Commit: `c59f99f` - task-129: Add 17 safe-wildcard bash patterns to ralph-init template allowlist

task-reviewer verdict: APPROVED (c59f99f). All ACs satisfied: #1 exact 17-entry set match, #2 count 30->47, #4 destructive-guard clean; #3 deferred for manual smoke test per sibling task-128 precedent (reviewer accepted under rule R2). Pre-existing unrelated timeout-handling test failure independently confirmed by reviewer. Code review PASS, change-relevant checks PASS.
<!-- SECTION:NOTES:END -->
