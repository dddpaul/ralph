---
id: TASK-130
title: >-
  Fix or document :* wildcard not matching no-arg invocations in ralph-init
  narrow rules
status: To Do
assignee: []
created_date: '2026-05-19 08:45'
labels: []
dependencies:
  - TASK-127
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Split from TASK-127 (Section D — the empirical bug). The user observed during a fresh ralph-init session that:

- Permission rule: `Bash(bash $HOME/.claude/skills/ralph-run/scripts/wait-heartbeat.sh:*)`
- Invocation: `bash $HOME/.claude/skills/ralph-run/scripts/wait-heartbeat.sh` (no trailing args)
- Result: **still prompts** despite the narrow rule existing.
- Fix that worked: add an additional exact-form rule `Bash(bash $HOME/.../wait-heartbeat.sh)` (no `:*`).

This implies Claude Code's matcher treats `:*` as 'requires at least one trailing token' rather than 'zero-or-more'. Both `wait-heartbeat.sh` and `utc-to-moscow.sh` have legitimate no-arg call sites in their parent skills (`wait-heartbeat.sh` is called bare from ralph-run; `utc-to-moscow.sh` is always called with an argument so may be fine — verify in repro). `preflight.sh` is always called with args.

## Investigation needed first

Before patching ralph-init, run a controlled minimal repro to confirm the hypothesis:

```bash
# In a throwaway project with one rule installed:
# Bash(bash /tmp/probe.sh:*)
# Compare these two invocations:
bash /tmp/probe.sh         # does this prompt?
bash /tmp/probe.sh foo     # does this prompt?
```

If confirmed, the fix is to extend Step 3.7b of `skills/ralph-init/SKILL.md` to emit the no-`:*` variant in parallel with the existing `:*` form for scripts known to be called bare.

## Scope

If repro confirms the hypothesis:

- `skills/ralph-init/SKILL.md` Step 3.7b extension: emit no-`:*` variants in both absolute-path and $HOME-form for `wait-heartbeat.sh` (and any other script the repro shows needs it). Result: 12 rules total per fresh init (6 from TASK-126's both-forms split, plus 6 no-`:*` variants).
- `skills/ralph-init/SKILL.md` Step 3.10 verification: extend expected[] arrays to check both `:*` and no-`:*` forms; failures should name which suffix is missing.
- `skills/ralph-init/SKILL.md` Step 3.7b note: add a second pitfall paragraph (alongside TASK-126's literal-match note) documenting that `:*` requires ≥1 trailing token.

If repro refutes the hypothesis: close the task with the controlled-repro evidence in notes; the user's earlier fix probably worked for an unrelated reason (caching, session restart, etc.).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Minimal controlled repro of the :* vs no-arg invocation behavior is recorded verbatim in the task notes (one rule, two invocations, both outcomes)
- [ ] #2 If repro confirms the pitfall: skills/ralph-init/SKILL.md Step 3.7b emits no-:* variants alongside the existing :* form for wait-heartbeat.sh in BOTH absolute and $HOME forms
- [ ] #3 If repro confirms: utc-to-moscow.sh is reviewed — either added or explicitly noted as not needing the no-:* variant because all call sites pass an argument
- [ ] #4 If repro confirms: skills/ralph-init/SKILL.md Step 3.10 verification block checks both suffix forms; WARN message names the specific missing suffix
- [ ] #5 If repro confirms: skills/ralph-init/SKILL.md Step 3.7b note documents the :* no-arg pitfall in the same paragraph that already documents the literal-match gotcha (from TASK-126)
- [ ] #6 If repro refutes: task notes record the negative result with the exact session evidence; task is closed as not-needed without code changes
<!-- AC:END -->
