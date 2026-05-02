---
id: TASK-86
title: Fix two silent regex bugs in task-validator.sh
status: In Progress
assignee: []
created_date: '2026-05-02 06:11'
updated_date: '2026-05-02 06:48'
labels:
  - validator
  - bug
  - hook
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Code review of TASK-82 found two silent regex bugs in .claude/hooks/task-validator.sh that reduce validator effectiveness. Both should be fixed so the validator delivers its primary value (catching AC duplication and AC-text contradictions during interactive task crafting).

## Bug A — AC dedup normalization broken (line 59)

The normalization sed uses basic regex (BRE), where '(x| )' is treated as literal text, not an alternation:

    NORMALIZED_ACS=$(echo "$AC_LINES" | sed 's/^[[:space:]]*- \[(x| )\][[:space:]]*//' ...)

The substitution never matches a real checkbox, so the strings are not normalized. AC #1 and AC #2 remain distinguished by their '#N ' index prefix (which the next sed strips), but the underlying issue is the BRE/ERE mismatch. Net effect: deterministic check #4 ('No identical AC strings after normalization') silently never fires.

Fix: switch to 'sed -E' so the parens and pipe behave as alternation, OR escape them in BRE form: 'sed "s/^[[:space:]]*- \\[\\(x\\| \\)\\][[:space:]]*//"'. Prefer the '-E' form.

Verification: write two identical AC lines to a fixture task, run the validator manually, confirm 'Validator [det]: Duplicate acceptance criteria detected' is emitted.

## Bug B — substantive-edit predicate excludes most AC changes (lines 165-167)

The substantive-edit filter explicitly removes lines of the form '+- [(x| )] #N <text>' from the candidate diff:

    SUBST_ADDED=$(... | grep -vE '^\\+- \\[(x| )\\] #[0-9]+ [A-Z]' || true)
    AC_TEXT_CHANGED=$(... | grep -vE '^\\+- \\[(x| )\\] #[0-9]+\\s' || true)

Every standard backlog AC line matches that exclusion ('+- [ ] #5 <criterion>'), so:
- Adding a brand-new AC via --ac "Verify X" is NOT classified as substantive → no LLM nudge fires.
- In-place AC text edits also fail to register (the unified diff '+'-line still matches '+- [ ] #N ...').

This contradicts AC #4 of TASK-82: 'Substantive-edit predicate uses git diff HEAD ... and only fires the LLM nudge when description body or AC text changed'. AC text changes are intended to be substantive. The smoke test #12 from TASK-82 (introduce a contradicting AC, validator flags it) cannot pass because the LLM nudge never fires for AC additions.

Fix: drop the exclusion that filters '#N'-prefixed lines, OR invert it (AC text changes ARE substantive). Concretely, AC_TEXT_CHANGED should include AC lines, not exclude them. SUBST_ADDED's '[A-Z]' filter is also nonsense — remove it.

After the fix, the predicate should classify the following as substantive:
- Description body lines added/removed (existing behavior; keep)
- New AC lines added (currently broken; should fire)
- AC text replacements where the only changed token is inside an existing AC line (currently broken; should fire)

It should still skip:
- AC checkbox flips ('- [ ] #N text' → '- [x] #N text' — only the checkbox character changed, not the text)
- frontmatter-only changes (status, updated_date, dependencies metadata)
- Notes-section appends
- Section-marker comments

Verification:
- 'backlog task edit N --ac "contradicting criterion"' on a task with an existing 'Use TypeScript' AC fires an LLM nudge with item #1 (contradiction) flagged.
- 'backlog task edit N --check-ac 1' fires no LLM nudge.
- 'backlog task edit N --append-notes "..."' fires no LLM nudge.

## Scope

Apply the same fixes to skills/ralph-init/templates/task-validator.sh so future projects ship the corrected validator.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Line 59 normalization uses 'sed -E' (or escaped BRE) so the checkbox prefix is actually stripped from each AC line
- [x] #2 Manual smoke test: two identical AC strings on the same task produce 'Validator [det]: Duplicate acceptance criteria detected'
- [x] #3 Substantive-edit predicate (lines 165-167) no longer excludes '+- [ ] #N <text>' lines from the candidate diff
- [x] #4 The nonsense '[A-Z]' filter on SUBST_ADDED is removed
- [x] #5 Manual smoke test: 'backlog task edit N --ac "new criterion"' produces a 'Validator [llm]: task-N' system-reminder block
- [x] #6 Manual smoke test: 'backlog task edit N --check-ac 1' does NOT produce an LLM nudge (only checkbox state changed)
- [x] #7 Manual smoke test: 'backlog task edit N --append-notes "..."' does NOT produce an LLM nudge
- [x] #8 Manual smoke test: 'backlog task edit N -d "<new desc body>"' produces an LLM nudge
- [x] #9 Same fixes applied to skills/ralph-init/templates/task-validator.sh; templates and .claude/hooks/ remain in sync (diff -q clean)
- [x] #10 Manual smoke test from TASK-82 #12 now passes: introducing a contradicting AC produces an LLM-nudged contradiction flag in the next reply
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Fix Bug A (line 59) by adding -E flag to sed for ERE alternation. Fix Bug B (lines 165-167) by rewriting substantive-edit predicate so AC text additions/changes are classified as substantive, while checkbox-only flips are excluded. Apply same fixes to template. Verify with smoke tests.
<!-- SECTION:NOTES:END -->
