---
id: TASK-177
title: Repoint ralph-init permission rules from deleted bash helpers to uv run
status: Done
assignee:
  - Claude
created_date: '2026-06-28 11:52'
updated_date: '2026-06-28 12:00'
labels: []
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up from the ralph-python-refactor final-cutover review (design/ralph-python-refactor-review-2026-06-28.md, Drift item). TASK-156 deleted skills/ralph-run/scripts/{preflight.sh,wait-heartbeat.sh} and repointed the ralph-run skill to invoke 'uv run python -m ralph.preflight|wait_heartbeat'. But skills/ralph-init/SKILL.md still bootstraps DEAD permission rules pointing at those deleted scripts, so a fresh /ralph-init (init OR upgrade) seeds inert allow-rules and its narrative describes helpers that no longer exist.

Runtime-inert (permission check is at the Bash-tool layer; stale allow rules are simply never matched), but a real cosmetic/correctness seam to close.

Scope is skills/ralph-init/SKILL.md ONLY. The template settings.local.json (skills/ralph-init/templates/claude/settings.local.json) was ALREADY updated in TASK-156 to carry 'Bash(uv run:*)' — this task makes the 3.7b merge + 3.10 verification + narrative consistent with that.

Sites to change (verified line numbers as of cutover):
- Step 3.7b (lines ~197-231): the jq narrow-rule merge writes 6 rules — preflight.sh (RULE1A/1B), wait-heartbeat.sh (RULE2A/2B), utc-to-moscow.sh (RULE3A/3B). The 4 preflight/wait-heartbeat rules now point at deleted scripts. Replace them with a SINGLE 'Bash(uv run:*)' rule (covers both 'uv run python -m ralph.preflight' and 'uv run python -m ralph.wait_heartbeat'). KEEP the utc-to-moscow.sh pair (that script still exists, still invoked bash-path by ralph-status). Net: merge goes from 6 rules to 3 (uv run + 2 utc-to-moscow forms).
- The 'both forms required' literal-match gotcha narrative (lines ~201-216): update so it no longer lists preflight.sh/wait-heartbeat.sh as bash-path invocations; the dual-form gotcha now applies only to utc-to-moscow.sh. uv run needs only the single form.
- Step 3.10 verification block (lines ~280-313): drop preflight.sh + wait-heartbeat.sh from expected_abs/expected_home arrays; add a presence check for 'Bash(uv run:*)'; keep utc-to-moscow.sh. Update the PASS/count message accordingly.
- Upgrade step (line ~552): 'writes both the absolute-path and literal-$HOME forms of the preflight.sh, wait-heartbeat.sh, and utc-to-moscow.sh rules — 6 rules total' — update the script list and count to match the new rule set.
- Line ~203 example placeholder referencing '<absolute-path-to-scripts/preflight.sh>' — reword to a still-valid example (e.g. the utc-to-moscow.sh resolver) or drop the preflight mention.

Verification: after edits, 'grep -nE "preflight.sh|wait-heartbeat.sh" skills/ralph-init/SKILL.md' must return NO matches. The jq blocks must remain valid (no broken code fences). This is a documentation/skill task — no Python/pytest impact, but run 'uv run ruff check .' as a no-op sanity and confirm the SKILL.md renders (balanced fences).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Step 3.7b jq merge in skills/ralph-init/SKILL.md no longer adds Bash(...preflight.sh:*) or Bash(...wait-heartbeat.sh:*) rules; it adds a single Bash(uv run:*) rule plus the two utc-to-moscow.sh forms (3 rules total)
- [x] #2 The 'both forms required' literal-match narrative is updated to describe only utc-to-moscow.sh (the dual $HOME/absolute gotcha); preflight.sh/wait-heartbeat.sh are no longer described as bash-path invocations
- [x] #3 Step 3.10 verification block drops preflight.sh and wait-heartbeat.sh from its expected arrays, adds a presence check for Bash(uv run:*), keeps utc-to-moscow.sh, and updates the PASS/count message
- [x] #4 The upgrade step (~line 552) rule list and count are updated to match the new rule set (no preflight.sh/wait-heartbeat.sh)
- [x] #5 grep -nE 'preflight.sh|wait-heartbeat.sh' skills/ralph-init/SKILL.md returns no matches
- [x] #6 All jq/bash code fences in the edited sections remain balanced and valid; uv run ruff check . passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan:
1. Replace Step 3.7b jq merge (lines ~197-231): drop 4 preflight/wait-heartbeat rules; replace with single Bash(uv run:*) rule; keep 2 utc-to-moscow.sh forms. Net: 6 rules -> 3 rules.
2. Update 'both forms required' narrative (lines ~201-216): scope dual $HOME/absolute gotcha to utc-to-moscow.sh only; uv run needs only the single form.
3. Update example placeholder at line 203 (drop preflight.sh; use utc-to-moscow.sh instead).
4. Step 3.10 verification (lines ~280-313): drop preflight.sh/wait-heartbeat.sh from expected_abs/expected_home arrays; add Bash(uv run:*) presence check; update PASS message count.
5. Upgrade step at line 552: update script list to (uv run + utc-to-moscow.sh) and count to 3.
6. Verify: grep -nE 'preflight.sh|wait-heartbeat.sh' skills/ralph-init/SKILL.md returns no matches; uv run ruff check . passes.

Commit: `1d02451` - task-177: Repoint ralph-init permission rules from deleted bash helpers to uv run

Reviewer APPROVED. Implemented:
- Step 3.7b jq merge collapsed from 6 rules to 3 (Bash(uv run:*) + 2 utc-to-moscow.sh forms).
- Narrative scoped dual-form gotcha to utc-to-moscow.sh only; uv run noted as single literal.
- Step 3.10 verification: dropped preflight/wait-heartbeat arrays, added Bash(uv run:*) presence check, PASS message now reports 3 rules.
- Upgrade U4 bullet: rule list + count updated.
- AC#5 verified: grep -nE 'preflight.sh|wait-heartbeat.sh' returns no matches.
- AC#6 verified: 34 fences balanced; uv run ruff check . passes; 185 pytest tests pass.
<!-- SECTION:NOTES:END -->
