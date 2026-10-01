---
id: TASK-254
title: Strip dead helper allow-rules and document reliance on sandbox auto-allow
status: Done
assignee: []
created_date: '2026-09-30 10:29'
updated_date: '2026-10-01 05:22'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

ralph-init deliberately stopped seeding allow-rules for the three read-only helper scripts (`preflight.sh`, `wait-heartbeat.sh`, `utc-to-moscow.sh`), on the stated assumption that `autoAllowBashIfSandboxed` authorizes them with no prompt. `plugins/ralph/skills/ralph-init/SKILL.md` says so in three places (around lines 382 and 488-489: "no prompt", "no seeded allow-rule is required").

That assumption does not hold on the Claude Code versions people are running. The upstream changelog records the fix only in **2.1.285**: *"Fixed sandbox auto-allow asking for approval on every run of many inline scripts containing equals signs."* On anything earlier, sandbox auto-allow fails for commands that begin with a shell assignment — and the snippet ralph-status-watch tells the agent to run is exactly that shape:

```bash
utc_iso="<completed_at value>"
moscow_time=$(bash ${CLAUDE_PLUGIN_ROOT}/skills/ralph-status/scripts/utc-to-moscow.sh "$utc_iso")
```

Measured in a real session on Claude Code 2.1.274 (Homebrew, installed 2026-09-27; the current Homebrew cask is 2.1.280, so no released build carries the fix yet): every Ralph launch asks twice (preflight + heartbeat wait) and every watch tick asks once. In that session 390 of 2472 Bash calls began with a `VAR=` assignment.

A second, independent breakage hits projects bootstrapped before the marketplace migration. Their `.claude/settings.local.json` still allows the pre-plugin paths:

```
Bash(bash $HOME/.claude/skills/ralph-run/scripts/preflight.sh:*)
Bash(bash $HOME/.claude/skills/ralph-run/scripts/wait-heartbeat.sh:*)
Bash(bash $HOME/.claude/skills/ralph-status/scripts/utc-to-moscow.sh:*)
```

Those files no longer exist — the skills live in the plugin cache now. Nothing removes the dead rules on upgrade, and nothing replaces them.

Note when writing the replacement rules: the plugin-cache path carries the version (`~/.claude/plugins/cache/dddpaul-ralph/ralph/0.8.1/skills/...`), so a rule naming a concrete version dies at the next plugin upgrade — eight versions were cached on one machine, six of them in a single day. The pattern has to survive an upgrade. Verify the chosen pattern actually matches before closing; on Claude Code before 2.1.282 a mid-pattern wildcard was skipped in settings files, so a rule that looks right may still not fire.

Also worth checking while here, but do not guess: plugin skills are addressed as `ralph:ralph-run`, while the template seeds bare `Skill(ralph-run)`. If the bare form no longer matches, fix it; if it does, leave it and say so in the task notes.

## Scope

In scope:
- Seed allow-rules for the three helper scripts in the ralph-init template `settings.local.json`, with a pattern that survives a plugin version bump.
- Mirror the same rules into the repo own live `.claude/settings.local.json` (R11 template parity).
- Add an Upgrade Mode migration that strips the dead `$HOME/.claude/skills/ralph-*` helper rules from an existing project `settings.local.json`.
- Correct the three SKILL.md passages that promise "no prompt" / "no seeded allow-rule is required".
- Check whether `Skill(ralph-run)` still matches a plugin skill and record the finding.

Out of scope:
- Changing `sandbox.enabled` or `autoAllowBashIfSandboxed` defaults.
- Changing how the skills invoke the helpers (the `${CLAUDE_PLUGIN_ROOT}` form stays).
- Anything about the Claude Code sandbox itself — the fix is upstream and already released.

## Files

- `plugins/ralph/skills/ralph-init/templates/claude/settings.local.json` (exists) — seeded allow-list; add the helper rules here.
- `.claude/settings.local.json` (exists) — the repo live copy; R11 requires it to match the template.
- `plugins/ralph/skills/ralph-init/SKILL.md` (exists) — holds the "no prompt" claims and Upgrade Mode; both change here.
- `plugins/ralph/skills/ralph-status-watch/SKILL.md` (exists) — the `utc_iso=` snippet that triggers the auto-allow failure.
- `plugins/ralph/skills/ralph-run/SKILL.md` (exists) — invokes preflight and wait-heartbeat.

## Source

Source: /Users/paul/Private/Alfa/Projects/enterprise@6cc988e2ad51

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, build command, or visible behavior — not "works correctly").
3. All dependencies in the task frontmatter are status=Done.
4. Out-of-scope items are not accidentally pulled in by ambiguous AC.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 No helper allow-rule is seeded in templates/claude/settings.local.json, and ralph-init SKILL.md Step 3.7a records why: sandbox auto-allow covers the helpers on the Claude Code version in use, and every measured rule shape is either over-broad under R6 or version-pinned
- [x] #2 No seeded allow-rule contains a concrete plugin version number: grep -E 'ralph/[0-9]+\.[0-9]+\.[0-9]+' over both settings.local.json files returns nothing
- [x] #3 .claude/settings.local.json carries no helper rules, matching the template (R11 parity)
- [x] #4 Candidate rule patterns were verified against the Claude Code version in use, and the verification method plus results are recorded in the task notes
- [x] #5 ralph-init Upgrade Mode removes allow-rules naming $HOME/.claude/skills/ralph-run or $HOME/.claude/skills/ralph-status from an existing project settings.local.json, and reports what it removed
- [x] #6 plugins/ralph/skills/ralph-init/SKILL.md ties the helpers' no-prompt behaviour to the Claude Code version it was measured on, and tells hosts on older builds to upgrade Claude Code rather than seed a rule
- [x] #7 Whether Skill(ralph-run) still matches a plugin skill was checked, and the finding recorded in the task notes
- [x] #8 uv run ruff check . and uv run pytest both pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: single $HOME-relative coarse prefix rule Bash(bash $HOME/.claude/plugins/cache/dddpaul-ralph/ralph/:*) in template + live settings.local.json (user decision: trailing wildcard avoids the pre-2.1.282 mid-pattern-wildcard bug and survives plugin bumps); strip this repo's three dead ralph/0.1.0 rules; extend the Upgrade Mode migration to cover stale version-pinned plugin-cache rules as well as $HOME/.claude/skills/ralph-*; correct SKILL.md 382/466/488-490/671; check Skill(ralph-run) vs ralph:ralph-run; verify the pattern fires by observation and record it. Run mode: interactive on host (the container cannot observe permission prompts and masks .claude/settings.local.json).

Design corrections found during implementation:
- The rule cannot be written as $HOME: Claude Code's matcher compares literal text and never expands variables (TASK-126), and the harness renders ${CLAUDE_PLUGIN_ROOT} to an absolute path. The template carries a {{CLAUDE_DIR}} placeholder; Step 3.7a renders it with ${CLAUDE_CONFIG_DIR:-$HOME/.claude}, the same resolution ralph.sh uses.
- No Bash(bash ...) prefix rule can match a command whose text starts with VAR=. ralph-status and ralph-status-watch called utc-to-moscow.sh behind utc_iso=/moscow_time= assignments, so both snippets now call it as a single bash command with the timestamp inlined (user-approved scope extension; the ${CLAUDE_PLUGIN_ROOT} form is unchanged).
- AC #3 wording says 'the same three rules'; the agreed pattern (user decision) is one prefix rule covering all three helpers. The live file carries the same single rule as the rendered template.
- AC #5 extended: the migration also strips version-pinned plugin-cache helper rules (.../ralph/X.Y.Z/...), the dead shape actually present in this repo, alongside the pre-marketplace .claude/skills/ralph-(run|status) shape.
- The U4 dead-rule regex first shipped with doubled backslashes inside single quotes, which jq read as 'literal backslash' and which matched nothing; caught by executing the snippet against a fixture, fixed, and pinned by tests/python/test_helper_allow_rule.py (mutation-tested against both this and an assignment-led helper call).

Live migration run on this repo's .claude/settings.local.json with the SKILL.md snippet: removed the three ralph/0.1.0 helper rules (dead: no 0.1.0 cache exists), added Bash(bash /Users/paul/.claude/plugins/cache/dddpaul-ralph/ralph/:*).

AC #7 (Skill(ralph-run) vs ralph:ralph-run): invoked the ralph:ralph-status skill in an interactive host session (auto mode off) with only bare Skill(ralph-status) in the allowlist; the user observed no prompt. No fix needed; bare Skill(...) entries left unchanged.

AC #4 'before' round, host Claude Code 2.1.280, interactive, auto mode off, user observing; live allowlist held only dead ralph/0.1.0 helper rules (which cannot match a 0.8.1 path):
  T1 bash <cache>/0.8.1/.../utc-to-moscow.sh "2026-09-30T10:00:00Z"  -> no prompt
  T2 utc_iso="..."; bash <cache>/.../utc-to-moscow.sh "$utc_iso"   -> no prompt
  T3 bash <cache>/.../utc-to-moscow.sh "probe=1"                    -> no prompt
  T5 the old two-line snippet verbatim (utc_iso=... newline moscow_time=$(bash ...)) -> no prompt
Sandbox auto-allow covers every helper shape on 2.1.280, so the handoff's symptom (measured on 2.1.274) does not reproduce here, and an interactive A/B on this host cannot show the rule matching.

AC #4 verification (headless A/B, isolates the matcher from sandbox auto-allow). Method: scratch project per rule with sandbox.enabled=false and only that rule in .claude/settings.local.json; /opt/homebrew/bin/claude -p --model haiku --setting-sources project,local --permission-mode default --output-format json, asked to run the helper once. In -p mode an unmatched command is denied and recorded in permission_denials. Claude Code 2.1.280.

Round 1 (utc-to-moscow.sh "2026-09-30T10:00:00Z"):
  no rule                              -> DENIED (denials 1)   control
  Bash(bash <C>/ralph/:*)              -> DENIED (denials 1)   the first implementation: does NOT match
Round 2:
  Bash(bash <C>/ralph/0.8.1/skills/ralph-status/scripts/utc-to-moscow.sh:*) -> RAN (0)  positive control
  Bash(bash <C>/ralph/*)                                                    -> RAN (0)  trailing glob matches
  Bash(bash <C>/ralph/*/skills/ralph-status/scripts/utc-to-moscow.sh:*)     -> DENIED (1) mid-pattern glob
(<C> = /Users/paul/.claude/plugins/cache/dddpaul-ralph)
Finding: ':*' is a word-boundary prefix and cannot end mid-path; a bare trailing '*' crosses '/'. Rule switched to Bash(bash {{CLAUDE_DIR}}/plugins/cache/dddpaul-ralph/ralph/*) everywhere; the measured table is recorded in ralph-init SKILL.md Step 3.7a.

Round 3, end to end: rendered the real template with the real Step 3.7a snippet (rule: Bash(bash /Users/paul/.claude/plugins/cache/dddpaul-ralph/ralph/*)), sandbox off:
  H1 bash <C>/ralph/0.8.1/skills/ralph-run/scripts/preflight.sh ./ralph.sh true --tasks 1 -> RAN (0)
  H2 bash <C>/ralph/0.8.1/skills/ralph-run/scripts/wait-heartbeat.sh                      -> RAN (0)
  H3 bash <C>/ralph/0.8.1/skills/ralph-status/scripts/utc-to-moscow.sh "2026-09-30T10:00:00Z" -> RAN (0)

Commit: `5b8f39d` - task-254: seed a version-independent allow-rule for the plugin helper scripts

task-reviewer round 1: CHANGES REQUESTED. Blocking (R6): a bare trailing '*' crosses '/', so Bash(bash <C>/ralph/*) auto-allows bash on every file in every cached plugin version (ralph.sh templates, patchers, init-firewall.sh) and possibly on ralph/../ traversal paths -- effectively the Bash(bash:*) R6 forbids; R13 says notes cannot waive it. The reviewer asked the main session to run a traversal probe it had been blocked from running; not run (surfaced to the user instead).

User decision: drop the seeded rule. Evidence: on Claude Code 2.1.280 sandbox auto-allow approved every helper shape with no prompt (T1-T5 above), so the rule fixes a symptom this host does not have, at an R6 cost. Kept: the dead-rule migration, the utc-to-moscow snippet collapse, and the SKILL.md corrections, reworded to the measured truth (auto-allow covers the helpers on 2.1.280; older builds should upgrade Claude Code). The {{CLAUDE_DIR}} render machinery was removed with the rule; the template is byte-identical to master. Live .claude/settings.local.json: rule removed; its allow set now equals the template's.

ACs #1, #3, #4 and #6 reworded to match the decision (they asked for the rule that was rejected). Reviewer nits folded in: the strip now tolerates a file with no permissions.allow (previously exit 5), and the test runs the jq lines from SKILL.md rather than re-checking the regex in Python.

Commit: `824460e` - task-254: drop the seeded helper rule and strip dead helper rules on upgrade

task-reviewer round 2: CHANGES REQUESTED (R12). ralph-status:65 and ralph-status-watch:75 still justified the single-bash call shape by a seeded allow-rule that no longer exists; ralph-run:83 promised auto-allow without naming the measured version. All three reworded to point at sandbox auto-allow and ralph-init Step 3.7a, with the version named in ralph-run. Added test_no_skill_still_cites_a_seeded_helper_rule (mutation-checked: fails with the stale sentence restored). Full pytest hit the known-flaky test_orchestrator_exits_promptly_on_sigterm once (-15 vs 130); passes alone and on a full re-run (673 passed).

Commit: `704c1ba` - task-254: point the helper call-shape notes at sandbox auto-allow

task-reviewer round 3: APPROVED. Retitled from 'Seed allow-rules for plugin helper scripts instead of relying on sandbox auto-allow' (reviewer nit: the original title described the opposite of what shipped; the Description keeps the handoff's original text as the source contract, and these notes record the decision). Final gates: ruff clean; pytest 673 passed / 2 skipped; bats unit 110 with only #34/#35 (pre-existing, APFS-only).

Commit: `c761d0d` - task-254: bump plugin version to 0.8.2 (patch)
<!-- SECTION:NOTES:END -->
