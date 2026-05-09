---
id: TASK-113
title: >-
  Add xhigh effort level and update ralph.sh / ralph-run defaults to opus-4-7 +
  max
status: Done
assignee: []
created_date: '2026-05-09 18:51'
updated_date: '2026-05-09 18:57'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Update ralph.sh effort enum and defaults so the CLI matches the user preferences:

1. Add xhigh as a valid --effort level. Verified via "claude --help": levels are low | medium | high | xhigh | max.
2. Change default MODEL from claude-opus-4-6 to claude-opus-4-7 (latest Opus).
3. Change default EFFORT from medium to max.
4. Update ralph-run skill defaults table to reflect model=claude-opus-4-7 and effort=max.

R11 (template parity) requires updating all three ralph.sh copies identically:
- ./ralph.sh (live)
- ./skills/ralph-run/scripts/ralph.sh (skill-bundled)
- ./skills/ralph-init/templates/root/ralph.sh (template for new projects)

Plus skills/ralph-run/SKILL.md (skill source). User-global ~/.claude/skills/ralph-run/SKILL.md is propagated by ralph-sync after merge.

## Specific ralph.sh edits

Header comment (line 3):
  `--effort low|medium|high|max` -> `--effort low|medium|high|xhigh|max`

Help text (line 19-20 ish):
  --model default -> claude-opus-4-7
  --effort default -> max
  --effort enum -> low|medium|high|xhigh|max

Variable defaults (line 36-37):
  MODEL="claude-opus-4-6" -> MODEL="claude-opus-4-7"
  EFFORT="medium" -> EFFORT="max"

Validation (line 164):
  Add xhigh to the four-way OR check.

## SKILL.md edit

In the Defaults table (Step 1):
  - Add row: `model | claude-opus-4-7 | --model`
  - Update effort row default to: `max` (already correct)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ralph.sh accepts --effort xhigh without "Invalid effort level" error
- [x] #2 ralph.sh default MODEL constant is claude-opus-4-7
- [x] #3 ralph.sh default EFFORT constant is max
- [x] #4 ralph.sh --help output shows the 5 effort levels (low | medium | high | xhigh | max) and claude-opus-4-7 as default model
- [x] #5 skills/ralph-run/scripts/ralph.sh is byte-identical to ./ralph.sh (R11 parity verifiable via diff exit 0)
- [x] #6 skills/ralph-init/templates/root/ralph.sh is byte-identical to ./ralph.sh (R11 parity verifiable via diff exit 0)
- [x] #7 skills/ralph-run/SKILL.md Defaults table includes a model row with default claude-opus-4-7 and effort row default is max
- [x] #8 bash -n passes on all three ralph.sh copies and ./ralph.sh --effort xhigh --help exits 0
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Update all 3 ralph.sh copies (./ralph.sh, skills/ralph-run/scripts/ralph.sh, skills/ralph-init/templates/root/ralph.sh) — add xhigh to enum, change MODEL to claude-opus-4-7, change EFFORT to max, update --help text and header comment. Update skills/ralph-run/SKILL.md Defaults table. Verify byte-identical via diff and bash -n + smoke test.

Commit: `4fea02f` - task-113: Add xhigh effort level; ralph.sh and ralph-run defaults to opus-4-7 + max

All 8 ACs verified. ralph.sh: xhigh added to enum; MODEL=claude-opus-4-7; EFFORT=max; --help text updated. R11 parity restored across all 3 ralph.sh copies (diff exit 0). Side-effect: skill-bundled copy gained pre-existing missing RALPH_AUTONOMOUS guards (latent inconsistency fixed). SKILL.md: model row added to Defaults table, launch command + report line include --model, divergence note rewritten. Reviewer APPROVED.
<!-- SECTION:NOTES:END -->
