---
id: TASK-126
title: >-
  Permission rules literal-match mismatch: skills invoke via $HOME, ralph-init
  writes absolute paths
status: In Progress
assignee: []
created_date: '2026-05-18 11:16'
updated_date: '2026-05-18 12:59'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Problem

`ralph-init` writes narrow permission rules into the new project's `.claude/settings.local.json` using absolute paths — per Step 3.7b of `skills/ralph-init/SKILL.md`, which explicitly resolves `$HOME` at install time on purpose, because Claude Code permission patterns are **literal-match**.

Example rule written:
```
"Bash(bash /Users/paul/.claude/skills/ralph-status/scripts/utc-to-moscow.sh:*)"
```

But the skill bodies that **actually invoke** those scripts use `$HOME` in the literal command string:

- `skills/ralph-status-watch/SKILL.md`, Step 3 Rule (e):
  ```bash
  elif [ -x "$HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh" ]; then
    moscow_time=\$(bash "\$HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh" "\$utc_iso")
  fi
  ```
- `skills/ralph-run/SKILL.md`, Step 3:
  ```
  bash <absolute-path-to-scripts/preflight.sh> ...
  ```
  In practice Claude inserts the absolute path here (angle-bracket placeholder), so this one is fine. But `utc-to-moscow.sh` (referenced by ralph-status-watch via `\$HOME`) is NOT, and Claude reproduces the `\$HOME/...` form from SKILL.md verbatim.

Claude Code's permission matcher does NOT expand `\$HOME` before comparing — it compares literal strings. So `bash \$HOME/.claude/...` does not match `bash /Users/paul/.claude/...`. Result: **permission prompt fires on every call** of these helper scripts, even though a narrow rule "exists".

## Concrete user-facing symptom

Repro in any fresh ralph-init'd project: run `/ralph-run tasks=X watch=5m`, wait for completion, observe that every `utc-to-moscow.sh` invocation by `/ralph-status-watch` triggers a permission prompt. Same potentially for `wait-heartbeat.sh`.

Observed first by user `pavelderunovich@gmail.com` running ralph-init on `sfa-crm-engine`; verified by inspecting `.claude/settings.local.json` (rule present, absolute path) and the skill body (invocation via `\$HOME`).

## Local workaround (already applied in sfa-crm-engine, not pushed)

Added parallel `\$HOME`-form rules in `.claude/settings.local.json`:
```
"Bash(bash \$HOME/.claude/skills/ralph-run/scripts/preflight.sh:*)",
"Bash(bash \$HOME/.claude/skills/ralph-run/scripts/wait-heartbeat.sh:*)",
"Bash(bash \$HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh:*)"
```

With both forms in `allow`, the prompt stops firing. But `settings.local.json` is per-developer (gitignored) — every developer hits the same issue on every fresh init.

## Root-cause fix options

**Option A (recommended): `ralph-init` writes BOTH forms** — absolute path AND `\$HOME` form — into `settings.local.json` Step 3.7b. Step 3.10 verification then checks for both. Existing projects pick this up via `ralph upgrade` U4 special-merge for `settings.local.json` (currently re-runs Step 3.7b; needs to ensure both forms land idempotently).

**Option B: harden skill bodies to use absolute paths.** Doesn't help — \`\$USER\` / any other shell variable hits the same literal-match wall.

**Option C: tell Claude Code's matcher to glob-expand `\$HOME`.** Upstream Anthropic, out of our control.

Option A is the only viable lane.

## Affected files in this repo

- `skills/ralph-init/SKILL.md` Step 3.7b — extend the RULE list to 6 entries (3 absolute + 3 \$HOME form). Update jq merge accordingly.
- `skills/ralph-init/SKILL.md` Step 3.10 — verification loop checks for BOTH forms per script.
- `skills/ralph-init/SKILL.md` Note near Step 3.7b — document the literal-match gotcha explicitly.

## Out of scope

- Don't rewrite `skills/ralph-status-watch/SKILL.md` to avoid `\$HOME` — it's a portability idiom and doesn't address the matcher behavior.
- Don't touch tracked `settings.local.json` files (they're per-developer / gitignored).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-init/SKILL.md Step 3.7b extended: writes 6 narrow rules to settings.local.json (3 absolute-path + 3 $HOME-form) for preflight.sh, wait-heartbeat.sh, utc-to-moscow.sh; jq merge stays idempotent
- [x] #2 skills/ralph-init/SKILL.md Step 3.10 verification updated to check BOTH forms per script (absolute AND $HOME); a missing rule of either form surfaces as WARN naming the specific missing form
- [x] #3 skills/ralph-init/SKILL.md Note section near Step 3.7b explicitly documents the literal-match gotcha (Claude Code permission patterns are literal-match; $HOME is NOT expanded; skill bodies using $HOME need a matching $HOME-form rule)
- [x] #4 Existing projects bootstrapped from earlier ralph-init can run `ralph upgrade` and the U4 special-merge for settings.local.json picks up the new 3 $HOME-form rules without removing user-added custom permissions; tested manually on a fixture project
- [ ] #5 Manual smoke test on a freshly ralph-init'd project: /ralph-run tasks=N watch=5m completes one full iteration and does NOT trigger a permission prompt for utc-to-moscow.sh, preflight.sh, or wait-heartbeat.sh
<!-- AC:END -->



## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan:
1. Step 3.7b: extend the 3 RULE assignments to 6 by adding RULE1B/2B/3B single-quoted variants with literal $HOME. Pass all 6 into the jq merge; unique dedup keeps idempotency.
2. Step 3.7b note: explicitly document the literal-match gotcha (Claude Code permission patterns are literal-match; $HOME is not expanded; skill bodies referencing $HOME need a matching $HOME-form rule).
3. Step 3.10 verification: extend expected[] from 3 to 6 entries — paths AND $HOME-form strings — and tighten the missing-rule message to name the specific form.
4. Confirm Step U4 special-merge path: U4 already lives in upgrade flow; the merge re-runs Step 3.7b via jq + unique, so the 3 new $HOME-form rules land idempotently on upgrade without clobbering user customizations. No separate U4 edit needed unless current U4 docs explicitly list expected rules (will check).
5. Smoke test on a fixture project — verify /ralph-run with watch=5m completes without permission prompts for the three scripts.
<!-- SECTION:NOTES:END -->
