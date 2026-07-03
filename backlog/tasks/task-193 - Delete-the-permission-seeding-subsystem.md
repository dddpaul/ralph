---
id: TASK-193
title: Delete the permission-seeding subsystem
status: Done
assignee: []
created_date: '2026-07-03 09:37'
updated_date: '2026-07-03 15:23'
labels:
  - 'feature:ralph-marketplace'
dependencies:
  - TASK-191
  - TASK-192
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Remove the now-unnecessary permission seeding from ralph-init and the template narrow allow-rules, since sandbox auto-allow covers the helpers. See design/ralph-marketplace-prd.md US-007.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ralph-init Step 3.7b seeding and the permission-matching narrative are removed
- [x] #2 The three narrow Bash bash-HOME-.claude-skills allow-rules are removed from the ralph-init settings.local.json template
- [x] #3 ralph-init Step 3.10 no longer verifies those rules
- [x] #4 A documented smoke test shows a fresh ralph-init scaffold launching /ralph-run with zero prompts except the devcontainer bypass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan (autonomous, iter 6):
Context: TASK-191 already repointed helper invocations to ${CLAUDE_PLUGIN_ROOT}; TASK-192 made wait-heartbeat read-only. So all three helpers (preflight, wait-heartbeat, utc-to-moscow) are now read-only, and per design (autoAllowBashIfSandboxed authorizes by what a command touches, not script path) sandbox auto-allow covers them. The seeded Bash(bash $HOME/.claude/skills/...) narrow rules are now dead (skills emit ${CLAUDE_PLUGIN_ROOT} paths, not $HOME).

Edits to plugins/ralph/skills/ralph-init/SKILL.md:
- AC#1: delete Step 3.7b (narrow-rule jq seeding) + the permission-matching narrative (~L202-230).
- AC#2: template settings.local.json already has ZERO narrow .claude/skills rules (grep-confirmed) — they were seeded only, never templated; removing 3.7b removes them from scaffolded output. Renumber surviving pptx step 3.7c -> 3.7b and make it self-contained.
- AC#3: rewrite Step 3.10 to drop the narrow-rule verification block; keep only the pptx verification (Documentation/Mixed).
- Fix U4 upgrade path (L543): drop the narrow-rule re-merge, keep pptx merge.
- AC#4: add a documented manual smoke test (fresh scaffold -> /ralph-run -> zero prompts except the dangerouslyDisableSandbox launch bypass).
R6 not violated: no broad rules added, settings.local.json content unchanged; the 'require narrow rules' clause is conditioned on avoiding an annoying prompt by widening — n/a under sandbox auto-allow.

Plan validated (autonomous iter, 2026-07-03): premise holds — ralph-run/status now emit bash ${CLAUDE_PLUGIN_ROOT}/... (TASK-191) and both helpers are read-only (TASK-192 moved rm out of wait_heartbeat), so sandbox autoAllowBashIfSandboxed covers them; the $HOME/.claude/skills narrow rules are dead. Only edit target = plugins/ralph/skills/ralph-init/SKILL.md. Confirmed template settings.local.json already carries ZERO narrow .claude/skills rules (they were seeded by 3.7b, never templated) → AC#2 met by deleting 3.7b. Out of scope (left untouched): live .claude/settings.local.json (expanded /Users/paul paths) and R6 in task-reviewer-rules.md (R6's 'require narrow rules' is conditioned on widening to avoid a prompt — moot under sandbox auto-allow; R6 edits belong to US-009 anyway). pptx step 3.7c stays (out of US-007 scope) → renumbered to 3.7b, made self-contained. Smoke test (AC#4): new '## Verification: zero-prompt smoke test' section after Step 4 Summary; the single allowed prompt = dangerouslyDisableSandbox on ralph-run Step 4 launch.

Commit: `ff2c1f8` - task-193: Delete permission-seeding subsystem from ralph-init

Implemented & task-reviewer APPROVED (commit ff2c1f8). Single file changed: plugins/ralph/skills/ralph-init/SKILL.md (+47/-62). AC#1: deleted Step 3.7b (narrow-rule jq seeding: RULE_PRE/RULE_HB/RULE_UTC) + the literal-$HOME permission-matching narrative. AC#2: verified template settings.local.json carries ZERO narrow .claude/skills rules (they were seeded by 3.7b, never templated) — deleting the seeding step removes them from scaffolded output. AC#3: rewrote Step 3.10 to verify only the pptx rules (Documentation/Mixed); dropped the preflight/wait-heartbeat/utc-to-moscow expected_rules block. AC#4: added '## Verification: zero-prompt smoke test' — fresh Code-only scaffold + /ralph-run tasks=1 devcontainer=true, expected result table shows the dangerouslyDisableSandbox launch as the ONLY prompt; helpers auto-allowed by sandbox (heartbeat rm stays project-dir/sandbox-covered per TASK-192). Also: renumbered pptx step 3.7c->3.7b (self-contained), fixed U4 upgrade path to drop the dead narrow-rule re-merge. Out of scope (untouched): live .claude/settings.local.json, R6/R11 (US-009/TASK-195). Gate: ruff clean, 185 pytest passed.
<!-- SECTION:NOTES:END -->
