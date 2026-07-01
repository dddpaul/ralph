---
id: TASK-183
title: >-
  Seed all narrow permission rules as literal $HOME and pin matching command
  forms (no hardcoded absolute home)
status: Done
assignee: []
created_date: '2026-07-01 18:29'
updated_date: '2026-07-01 18:56'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
settings.local.json narrow rules hardcode an absolute /Users/<home> path AND fail to match what the agent actually types. Root cause: ralph-init Step 3.7b builds the rule strings with $HOME DOUBLE-quoted, so $HOME expands to /Users/paul at seed time — producing rules like Bash(PYTHONPATH=/Users/paul/.claude/skills/ralph-run/scripts uv run ... ralph.preflight:*). But the skills instruct the agent to TYPE $HOME (ralph-run Steps 3/4 use PYTHONPATH=<...>; ralph-status resolvers use $HOME/... ), and Claude Code matches command strings LITERALLY without expanding $HOME. So the emitted literal '$HOME/...' never matches the expanded '/Users/paul/...' rule -> permission prompt, and the rule is non-portable across machines. Fix (per canonicalize decision): (1) reduce each command to ONE deterministic literal-$HOME form in its skill, unquoted path; (2) seed every narrow rule as LITERAL $HOME by single-quoting the jq rule strings so $HOME is preserved; (3) drop the dead absolute utc form and the relative './' utc branch. Net: 3 narrow rules (ralph.preflight, ralph.wait_heartbeat, utc-to-moscow), all literal $HOME, each verbatim-matching the single command form its skill emits. Not in R11 template mirror (skill bodies); propagates via /ralph-sync. After merge, re-run ralph-init upgrade to reseed settings.local.json with the literal-$HOME rules.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-status/SKILL.md and skills/ralph-status-watch/SKILL.md: the utc-to-moscow resolver is reduced to a single deterministic invocation using a literal, unquoted $HOME path — bash $HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh "$utc_iso" — and the relative ./skills/... branch is removed
- [x] #2 grep for 'bash ./skills/ralph-status/scripts/utc-to-moscow.sh' returns nothing in either status SKILL.md
- [x] #3 skills/ralph-run/SKILL.md Step 3 (preflight) and Step 4 (wait_heartbeat) pin the command to the literal unquoted form PYTHONPATH=$HOME/.claude/skills/ralph-run/scripts uv run --no-project python -m ralph.preflight (and ...ralph.wait_heartbeat), replacing the <absolute-path-to-scripts-dir> placeholder, so the emitted string verbatim-matches the seeded rule
- [x] #4 skills/ralph-init/SKILL.md Step 3.7b builds all three narrow rule strings SINGLE-quoted so $HOME is preserved literally (not expanded): ralph.preflight, ralph.wait_heartbeat, and one utc-to-moscow — 3 rules total, none containing an expanded /Users or /home absolute path
- [x] #5 skills/ralph-init/SKILL.md 3.7b narrative corrected: no 'both forms required' and no 'absolute-path branch the resolver falls through to'; it states each rule must verbatim-match the single literal-$HOME command its skill emits, and that Claude Code matches command strings literally without expanding $HOME
- [x] #6 skills/ralph-init/SKILL.md Step 3.10 verification greps the three literal-$HOME rule strings (single-quoted greps), PASS message names 3 rules, and the U4 upgrade note is updated to '3 rules, literal $HOME'
- [x] #7 grep across skills/ralph-init/SKILL.md finds no narrow rule that expands $HOME to an absolute /Users or /home path, and the dead absolute utc-to-moscow rule is gone
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Canonicalize each helper command to ONE literal-$HOME form and seed matching narrow rules (3 total).
1. skills/ralph-status/SKILL.md Step 2.5 + skills/ralph-status-watch/SKILL.md Rule(e): collapse the ./skills-first / $HOME-elif resolver to a single line 'moscow_time=$(bash $HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh "$utc_iso")'; drop the relative ./ branch and stale resolver comment (AC1,AC2).
2. skills/ralph-run/SKILL.md Step 3 & Step 4: replace <absolute-path-to-scripts-dir> placeholder with literal 'PYTHONPATH=$HOME/.claude/skills/ralph-run/scripts ...' for ralph.preflight and ralph.wait_heartbeat; note verbatim-match requirement in prose (AC3).
3. skills/ralph-init/SKILL.md 3.7b: single-quote all 3 RULE_* strings (RULE_PRE, RULE_HB, one RULE_UTC), jq merges 3 rules; rewrite narrative (drop 'both forms required' + '/Users absolute-path branch', add literal-match verbatim + no-$HOME-expansion) (AC4,AC5).
4. skills/ralph-init/SKILL.md 3.10: greps become 3 single-quoted literal-$HOME rule strings, PASS names 3 rules; U4 note (line ~552) -> '3 rules, literal $HOME' (AC6,AC7).
Scope: skill bodies only; NOT R11-mirrored (no templates/ SKILL copy); template settings.local.json has no narrow rules. Lint: uv run ruff check . ; tests: uv run pytest. Then task-reviewer on git diff master..HEAD.

Commit: `d587ee6` - task-183: Canonicalize helper invocations to one literal-$HOME form and seed 3 matching narrow rules

Done (commit d587ee6). Canonicalized all three helper commands to a single literal-$HOME form and seeded 3 matching narrow rules.
- ralph-status/ralph-status-watch: utc-to-moscow resolver reduced to one 'bash $HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh "$utc_iso"' call; relative ./skills branch + stale comment removed (AC1,AC2).
- ralph-run Steps 3/4: placeholder replaced with literal 'PYTHONPATH=$HOME/.claude/skills/ralph-run/scripts uv run --no-project python -m ralph.preflight' (+wait_heartbeat); prose requires verbatim typing (AC3).
- ralph-init 3.7b: RULE_PRE/RULE_HB/RULE_UTC all single-quoted, jq merges 3 rules; narrative rewritten (dropped 'both forms required' + '/Users absolute-path branch'); now states verbatim single-form match + Claude Code matches literally w/o expanding $HOME (AC4,AC5). 3.10 greps 3 single-quoted literal-$HOME rules, PASS names 3; U4 note = '3 rules total, all literal $HOME' (AC6). No /Users or /home token remains; dead dual-form vars gone (AC7).
Verification: uv run ruff check . clean; uv run pytest 185 passed. End-to-end test of 3.7b jq merge on a template copy: exactly 3 literal-$HOME rules land, idempotent (allow len 51->51), 3.10 PASS. task-reviewer APPROVED. Scope: skill bodies only (propagate via /ralph-sync; not R11-mirrored). After merge, re-run ralph-init upgrade to reseed settings.local.json with the literal-$HOME rules.
<!-- SECTION:NOTES:END -->
