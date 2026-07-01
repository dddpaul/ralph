---
id: TASK-180
title: >-
  Narrow permission rules for Python-module preflight/heartbeat and fix
  utc-to-moscow quoted invocation
status: Done
assignee: []
created_date: '2026-07-01 09:59'
updated_date: '2026-07-01 13:54'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Interactive `/ralph-run` + `/ralph-status-watch` still fire permission prompts for three helper invocations, despite "narrow rules existing". Two root causes, both post-dating TASK-126:

1. **False premise in Step 3.7b (lines ~201, ~208).** ralph-init asserts preflight/heartbeat are "covered by the blanket `Bash(uv run:*)` rule" because "`uv run` is the literal command in every ralph-run invocation, with no `$HOME`/absolute split." That is wrong after the Python cutover (TASK-156): ralph-run Step 3/4 invoke them as `PYTHONPATH=<abs-scripts-dir> uv run --no-project python -m ralph.preflight` / `... ralph.wait_heartbeat`. The leading `PYTHONPATH=` env-assignment means the command does NOT start with `uv run`, so `Bash(uv run:*)` never matches (Claude Code matches literal prefixes). `preflight` is read-only so `autoAllowBashIfSandboxed` usually hides it; `wait_heartbeat` mutates the FS (removes the launch log) so it is NOT auto-sandbox-allowed → falls to the allow-list → env-prefix defeats the match → prompt.

2. **utc-to-moscow quoted-invocation gap.** TASK-126 seeded unquoted `$HOME`- and absolute-form rules for utc-to-moscow.sh. But ralph-status-watch Rule (e) `$HOME` branch invokes it QUOTED: `bash "$HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh" "$utc_iso"`. The `"` right after `bash ` makes the literal string differ from the unquoted rule → prompt (verified live).

Consumer hard constraint: do NOT rely on or reintroduce broad `Bash(uv run:*)` — it both fails here (env-prefix) and grants arbitrary `uv run` execution, which the downstream user rejected on security grounds. Rules must be narrow (exact module / exact script).

## Scope

In scope:
- Replace the `Bash(uv run:*)` reliance for preflight/heartbeat with two NARROW, per-module rules seeded at init (resolved absolute PYTHONPATH, mirroring how TASK-126 seeds the absolute-form utc-to-moscow rule).
- Remove the broad `Bash(uv run:*)` from the seeded template and Step 3.7b/3.10.
- Correct the false-premise note in Step 3.7b.
- Align the ralph-status-watch Rule (e) `$HOME` invocation of utc-to-moscow.sh so it matches the seeded unquoted `$HOME`-form rule.

Out of scope:
- Do NOT reintroduce broad `Bash(uv run:*)` anywhere.
- Do NOT touch per-developer gitignored `.claude/settings.local.json` files (only the template + Step 3.7b/3.10 + skill bodies).
- Do NOT change the Python orchestrator or the ralph-run invocation forms (`PYTHONPATH=... uv run python -m ...` stays) — fix rules + utc-to-moscow quoting only.
- Do NOT redo TASK-126's utc-to-moscow dual-form (keep it); only add the quoted-invocation alignment.

## Files

- `skills/ralph-init/SKILL.md` (exists) — Step 3.7b (~L201-222): false premise + rule seeding; Step 3.10 (~L277-304): verification loop.
- `skills/ralph-init/templates/claude/settings.local.json` (exists) — contains `Bash(uv run:*)` to remove.
- `skills/ralph-status-watch/SKILL.md` (exists) — Rule (e) `$HOME` branch (~L76) quoted utc-to-moscow invocation.
- `skills/ralph-run/SKILL.md` (exists, read-only context) — Steps 3/4 (~L82, L122) confirm the `PYTHONPATH=... uv run python -m ralph.preflight|wait_heartbeat` invocation form.

Prior art in this repo (Done): TASK-126 (utc-to-moscow $HOME/absolute dual-form), TASK-156 (Python cutover that changed the invocation), TASK-77 / TASK-85 (permission-narrowing history).

## Source

Source: /Users/paul/Private/Alfa/Projects/standard/stacks@7078804ea3d3-dirty
(Source is a documentation repo; this handoff emerged from a live /ralph-run debugging session there. No source design doc — full context is inline above + dest TASK-126/TASK-156.)

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (grep / build / observable behavior — not "works correctly").
3. Dependencies in frontmatter are status=Done (none hard-blocking; TASK-126/156 are Done context).
4. Out-of-scope items are not pulled in (no broad `uv run:*`, no per-dev settings.local.json edits).

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-init/SKILL.md Step 3.7b seeds two NARROW rules with resolved absolute PYTHONPATH — Bash(PYTHONPATH=<RESOLVED_HOME>/.claude/skills/ralph-run/scripts uv run --no-project python -m ralph.preflight:*) and the ralph.wait_heartbeat equivalent — instead of relying on Bash(uv run:*)
- [x] #2 skills/ralph-init/templates/claude/settings.local.json no longer contains Bash(uv run:*) (grep -F returns nothing)
- [x] #3 skills/ralph-init/SKILL.md Step 3.10 verification checks for the two new PYTHONPATH module rules and no longer expects Bash(uv run:*); a missing rule surfaces as WARN naming it
- [x] #4 The Step 3.7b note is corrected: preflight/heartbeat are invoked with a leading PYTHONPATH= env-assignment which defeats a Bash(uv run:*) prefix rule, so narrow env-prefixed rules are required
- [x] #5 skills/ralph-status-watch/SKILL.md Rule (e) $HOME branch invokes utc-to-moscow.sh WITHOUT quotes around the path (bash $HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh "$utc_iso"), matching the seeded $HOME-form rule
- [x] #6 No broad Bash(uv run:*) remains in the seeded template or Step 3.7b/3.10 (grep across both files returns nothing)
- [ ] #7 Smoke (may defer per R2 like TASK-126 AC#5): fresh ralph-init'd project, /ralph-run tasks=N watch=5m through completion fires zero permission prompts for preflight, wait_heartbeat, utc-to-moscow
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) ralph-init/templates/claude/settings.local.json — remove Bash(uv run:*). (2) ralph-init/SKILL.md Step 3.7b — correct false-premise note (leading PYTHONPATH= env-assignment defeats Bash(uv run:*) prefix match; wait_heartbeat mutates FS so not auto-sandboxed), change jq merge to seed 2 narrow env-prefixed rules (ralph.preflight + ralph.wait_heartbeat with resolved $HOME PYTHONPATH) + keep 2 utc-to-moscow forms, drop uv run rule. (3) Step 3.10 — verify the 2 module rules instead of Bash(uv run:*); WARN names any missing. (4) ralph-status-watch/SKILL.md Rule (e) $HOME branch — unquote bash path so it matches seeded $HOME-form rule. Out of scope but noted: ralph-status/SKILL.md L67 has same quoted-invocation bug (separate /ralph-status flow) -> log follow-up task.

AC#7 (smoke) DEFERRED per R2 (as AC text permits, mirroring TASK-126 AC#5): requires a fresh ralph-init-bootstrapped project and a live /ralph-run tasks=N watch=5m driven through completion to observe zero permission prompts — a live integration scenario not runnable inside this autonomous markdown/JSON editing iteration. Follow-up plan: verify on the next real interactive /ralph-run in a freshly-initialized project; the seeded-rule + verification logic was proven here by simulating the exact Step 3.7b jq merge + Step 3.10 block against a template copy ($HOME resolved to absolute /home/node/... PYTHONPATH, idempotent, PASS with all 4 rules, WARN naming a removed rule).

Commit: `3459172` - task-180: Seed narrow env-prefixed rules for preflight/heartbeat; fix utc-to-moscow quoting

DONE: task-reviewer APPROVED (git diff master..HEAD). AC#1-6 checked, AC#7 deferred per R2. Final gates: ruff clean, 185 pytest passed. Implemented: (1) removed broad Bash(uv run:*) from template settings.local.json; (2) ralph-init Step 3.7b seeds two narrow env-prefixed rules (resolved absolute PYTHONPATH for ralph.preflight + ralph.wait_heartbeat) + corrected false-premise note (leading PYTHONPATH= defeats uv-run prefix match; wait_heartbeat mutates FS so not auto-sandbox-allowed); Step 3.10 verifies the two module rules (WARN names missing); upgrade-path U-section updated to 4 rules total so upgrade won't re-seed Bash(uv run:*); (3) ralph-status-watch Rule (e) $HOME branch unquoted to match seeded literal-$HOME rule. R11 one-sided template change justified (live settings.local.json is untracked/gitignored + task out-of-scope). Follow-up filed for ralph-status/SKILL.md L67 (same quoted-invocation bug on the separate /ralph-status flow).
<!-- SECTION:NOTES:END -->
