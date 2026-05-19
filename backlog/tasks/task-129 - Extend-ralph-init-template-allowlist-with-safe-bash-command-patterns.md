---
id: TASK-129
title: Extend ralph-init template allowlist with safe bash command patterns
status: To Do
assignee: []
created_date: '2026-05-19 08:44'
updated_date: '2026-05-19 09:03'
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
- [ ] #1 templates/claude/settings.local.json adds exactly these 17 safe-wildcard entries: Bash(backlog task view:*), Bash(backlog task archive:*), Bash(backlog config:*), Bash(backlog doc view:*), Bash(backlog doc list:*), Bash(git checkout:*), Bash(git merge:*), Bash(git mv:*), Bash(git rm:*), Bash(mkdir:*), Bash(chmod:*), Bash(tee:*), Bash(jq:*), Bash(ps:*), Bash(tail:*), Bash(head:*), Bash(wc:*)
- [ ] #2 jq -r '.permissions.allow | length' on the template shows count = old count + 17
- [ ] #3 Smoke test on a freshly ralph-init'd project: running a normal Ralph task lifecycle (create branch via git checkout, jq merge during 3.7b, mkdir for scaffolding, git merge to master) does not trigger any permission prompt for the 17 listed safe commands
- [ ] #4 templates/claude/settings.local.json does NOT contain any of: Bash(rm:*), Bash(cp:*), Bash(mv:*), Bash(rmdir:*), Bash(kill:*), Bash(bash:*), Bash(sh:*), Bash(zsh:*) — verified by grep -E 'Bash\(rm:|Bash\(cp:|Bash\(mv:|Bash\(rmdir:|Bash\(kill:|Bash\(bash:|Bash\(sh:|Bash\(zsh:' returning no matches. Specific path-narrowed forms like Bash(bash $HOME/.claude/skills/.../script.sh:*) are still allowed because the colon does not immediately follow the shell name.
<!-- AC:END -->
