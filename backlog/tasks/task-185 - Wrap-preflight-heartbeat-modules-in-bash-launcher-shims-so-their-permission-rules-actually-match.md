---
id: TASK-185
title: >-
  Wrap preflight/heartbeat modules in bash launcher shims so their permission
  rules actually match
status: Done
assignee: []
created_date: '2026-07-01 20:42'
updated_date: '2026-07-02 05:52'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ROOT CAUSE (authoritatively confirmed): Claude Code parses a Bash command and keys the allow rule on the executable; it strips a fixed wrapper set (timeout/time/nice/nohup/stdbuf/xargs) but NOT inline env-var assignments. So a command that leads with 'PYTHONPATH=... uv run ...' cannot be matched by ANY allow rule — including one whose literal text repeats the same PYTHONPATH= prefix. This is why /ralph-run's preflight and wait_heartbeat still fire permission prompts despite TASK-180/183's seeded rules. The utc-to-moscow rule works only because it is invoked as 'bash <abs-path>' (no env prefix). TASK-156 introduced the regression by inlining the old preflight.sh/wait-heartbeat.sh wrappers into 'PYTHONPATH=... uv run python -m ...'.\n\nFIX (documented pattern): re-add TWO thin bash launcher shims (no orchestration logic — each just resolves its own dir as PYTHONPATH and execs the Python module), have /ralph-run invoke them as 'bash $HOME/.claude/skills/ralph-run/scripts/<name>.sh ...', and seed clean 'Bash(bash $HOME/.claude/skills/ralph-run/scripts/<name>.sh:*)' rules (single-quoted literal $HOME) — the exact pattern the utc-to-moscow rule uses and that never prompts. This does NOT reintroduce the deleted bash orchestrator; the orchestration stays in Python. Shim body:\n\n#\!/usr/bin/env bash\nSCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"\nPYTHONPATH="$SCRIPTS_DIR" exec uv run --no-project python -m ralph.preflight "$@"\n\nNot in R11 template mirror (scripts/skills, not .claude bootstrap); propagates via /ralph-sync. After merge+sync, re-run ralph-init upgrade to reseed settings.local.json with the wrapper rules. The utc-to-moscow rule from TASK-183 is already correct and stays.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 New skills/ralph-run/scripts/preflight.sh: executable thin bash shim that sets PYTHONPATH to its own directory and execs 'uv run --no-project python -m ralph.preflight "$@"' (no orchestration logic)
- [x] #2 New skills/ralph-run/scripts/wait-heartbeat.sh: same thin shim for ralph.wait_heartbeat
- [x] #3 skills/ralph-run/SKILL.md Step 3 invokes 'bash $HOME/.claude/skills/ralph-run/scripts/preflight.sh <args>' and Step 4 invokes 'bash $HOME/.claude/skills/ralph-run/scripts/wait-heartbeat.sh' — NO inline PYTHONPATH= env-var prefix remains in either step
- [x] #4 skills/ralph-init/SKILL.md Step 3.7b seeds the two module rules as clean bash-path forms — Bash(bash $HOME/.claude/skills/ralph-run/scripts/preflight.sh:*) and the wait-heartbeat.sh equivalent (single-quoted literal $HOME) — replacing the unmatchable PYTHONPATH=-prefixed rules; the utc-to-moscow rule is unchanged; 3 rules total, all 'bash <path>' form
- [x] #5 skills/ralph-init/SKILL.md 3.7b narrative corrected: states Claude Code cannot match an allow rule for a command that leads with an inline env-var assignment, so module invocations are wrapped in bash launcher shims and allow-listed as Bash(bash <abs-path>:*) (same pattern as utc-to-moscow); the prior 'PYTHONPATH= rule works' claim is removed
- [x] #6 skills/ralph-init/SKILL.md Step 3.10 verification greps the two wrapper-path rules plus the utc rule (all bash-path form) and its PASS message names 3 rules; U4 upgrade note consistent
- [x] #7 grep confirms no 'PYTHONPATH=' inline env prefix remains in skills/ralph-run/SKILL.md or in any seeded rule in skills/ralph-init/SKILL.md
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Add two thin bash launcher shims skills/ralph-run/scripts/{preflight.sh,wait-heartbeat.sh} — each resolves its own dir as PYTHONPATH via ${BASH_SOURCE[0]} and execs 'uv run --no-project python -m ralph.<mod> "$@"' (no orchestration logic; set -euo pipefail like sibling utc-to-moscow.sh). Verified VAR=val exec env-propagation + $@ passthrough work. (2) ralph-run/SKILL.md Step 3 -> 'bash $HOME/.claude/skills/ralph-run/scripts/preflight.sh <args>'; Step 4 -> 'bash $HOME/.claude/skills/ralph-run/scripts/wait-heartbeat.sh' — drop inline PYTHONPATH= prefix. (3) ralph-init/SKILL.md 3.7b: replace 2 PYTHONPATH rules with 2 clean Bash(bash $HOME/.../<name>.sh:*) rules (single-quoted literal $HOME); keep utc rule; 3 rules all bash-path. (4) 3.7b narrative: env-var-prefixed commands cannot match any allow rule -> wrap in bash shims allow-listed as Bash(bash <abs>:*), same as utc-to-moscow; remove 'PYTHONPATH= rule works' claim. (5) 3.10 verify greps 3 bash-path rules + PASS names 3; U4 note consistent. (6) grep no inline PYTHONPATH= remains. Not R11-mirrored (scripts/skills, not .claude bootstrap); propagates via ralph-sync.

Note on design/ralph-python-refactor-review-2026-06-28.md: that dated review of TASK-156's cutover recommended repointing ralph-init/SKILL.md to the 'python -m ralph.preflight|wait_heartbeat' entrypoints and dropping the .sh rules. TASK-185's root-cause finding SUPERSEDES that: the python-inline (PYTHONPATH=... uv run) form can never be allow-listed because Claude Code does not strip inline env-var assignments. The correct fix is bash launcher shims allow-listed as Bash(bash <abs>:*). The design doc is a point-in-time review artifact (not TASK-185's deliverable, not in this diff) and is intentionally left unmodified. Implementation-decision: added 'set -euo pipefail' and header comments to the shims (beyond the task's minimal 3-line body) to match the sibling utc-to-moscow.sh style; still thin (no orchestration). Verified: shims resolve their modules via own-dir PYTHONPATH (preflight.sh ran checks; wait-heartbeat.sh hit exit-2 path), ruff clean, 185 pytest pass, shims staged mode 100755. NOT R11-mirrored (scripts/skills dir, not .claude bootstrap); propagates via /ralph-sync; post-merge: re-run ralph-init upgrade to reseed live settings.local.json.

Commit: `2a7ac73` - task-185: Wrap preflight/heartbeat modules in bash launcher shims so allow rules match

Done: reviewer (task-reviewer agent) APPROVED — all 7 ACs traced, R5/R6/R11/R12/R13 pass. Final gate: ruff clean, 185 pytest pass, bash -n OK on both shims. Commit 2a7ac73 on task-185. Post-merge follow-up (out of scope here): run /ralph-sync then ralph-init upgrade to reseed live .claude/settings.local.json with the 2 bash-path wrapper rules (utc rule already correct).
<!-- SECTION:NOTES:END -->
