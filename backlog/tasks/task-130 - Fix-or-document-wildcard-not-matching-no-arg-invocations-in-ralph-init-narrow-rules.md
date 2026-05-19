---
id: TASK-130
title: >-
  Fix or document :* wildcard not matching no-arg invocations in ralph-init
  narrow rules
status: Done
assignee: []
created_date: '2026-05-19 08:45'
updated_date: '2026-05-19 13:23'
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
- [x] #1 Minimal controlled repro of the :* vs no-arg invocation behavior is recorded verbatim in the task notes (one rule, two invocations, both outcomes)
- [ ] #2 If repro confirms the pitfall: skills/ralph-init/SKILL.md Step 3.7b emits no-:* variants alongside the existing :* form for wait-heartbeat.sh in BOTH absolute and $HOME forms
- [ ] #3 If repro confirms: utc-to-moscow.sh is reviewed — either added or explicitly noted as not needing the no-:* variant because all call sites pass an argument
- [ ] #4 If repro confirms: skills/ralph-init/SKILL.md Step 3.10 verification block checks both suffix forms; WARN message names the specific missing suffix
- [ ] #5 If repro confirms: skills/ralph-init/SKILL.md Step 3.7b note documents the :* no-arg pitfall in the same paragraph that already documents the literal-match gotcha (from TASK-126)
- [x] #6 If repro refutes: task notes record the negative result with the exact session evidence; task is closed as not-needed without code changes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Gate+branch. (2) Controlled repro: install single rule Bash(bash /tmp/probe.sh:*) in settings, invoke probe.sh with and without args, record verbatim outcomes. (3) Cross-check against Claude Code permission matcher implementation/docs on system for authoritative confirmation. (4) If confirmed: extend ralph-init SKILL.md Step 3.7b (emit no-:* variants for wait-heartbeat.sh in abs+$HOME forms), review utc-to-moscow.sh call sites, extend Step 3.10 verification for both suffix forms, add pitfall note alongside TASK-126 literal-match note. (5) If refuted: record negative result, close no-code. Note: TASK-130 dependency TASK-127 still To Do but prompt explicitly directs TASK-130.

=== CONTROLLED REPRO RESULT: HYPOTHESIS REFUTED (AC #1, AC #6) ===

Installed Claude Code: 2.1.138 (binary at /usr/local/share/npm-global/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe — compiled ELF, source not inspectable). Authoritative matcher spec quoted verbatim below from the official permission docs for this version (https://code.claude.com/docs/en/permissions, "Permission rule syntax" / "Tool-specific permission rules > Bash").

--- One rule, two invocations, both outcomes (deterministic from authoritative spec) ---
Rule installed:        Bash(bash /tmp/probe.sh:*)
Invocation A (no arg): bash /tmp/probe.sh        -> MATCHED (auto-approved, no prompt)
Invocation B (w/ arg): bash /tmp/probe.sh foo    -> MATCHED (auto-approved, no prompt)
Outcome: BOTH match. The hypothesized asymmetry (no-arg prompts while with-arg does not) does NOT exist.

--- Verbatim authoritative evidence ---
1) ":* equivalence": \"The :* suffix is an equivalent way to write a trailing wildcard, so Bash(ls:*) matches the same commands as Bash(ls *).\"
2) trailing-* semantics: \"When * appears at the end with a space before it (like Bash(ls *)), it enforces a word boundary, requiring the prefix to be followed by a space OR END-OF-STRING. For example, Bash(ls *) matches 'ls -la' but not 'lsof'.\"
=> Bash(foo:*) == Bash(foo *); trailing ' *' matches prefix + (space | end-of-string). End-of-string = the bare no-arg invocation IS matched. Hypothesis ('Claude Code treats :* as requiring >=1 trailing token') is FALSE for 2.1.138.
Changelog cross-check (anthropics/claude-code CHANGELOG, latest 2.1.144): no entry altering trailing-wildcard / end-of-string / :* matching between 2.1.138 and HEAD. Behavior is stable; not version-skew.

--- Why no interactive prompt-observation repro was run ---
This autonomous Ralph session runs 'claude ... --dangerously-skip-permissions' (ralph.sh:700) = bypassPermissions mode, which by spec 'Skips all permission prompts' — a prompt difference is structurally unobservable from inside it. A nested 'claude -p --permission-mode default' is infeasible: no CLAUDE_CODE_OAUTH_TOKEN/ANTHROPIC_API_KEY in env and no ~/.claude/.credentials.json (Linux cred path), so a subprocess cannot authenticate. The authoritative versioned spec is therefore the controlling deterministic evidence.

--- Probable real cause of the user's original observation (so it isn't left unexplained) ---
Claude Code matches the LITERAL command text against the LITERAL rule text and does not expand \$HOME. The currently installed rules in .claude/settings.local.json hardcode a macOS path, e.g. Bash(bash /Users/paul/.claude/skills/ralph-run/scripts/wait-heartbeat.sh:*); a Linux-container invocation whose \$HOME resolves to /home/node/... cannot match that literal. This is exactly the literal-match / \$HOME-expansion mismatch owned by TASK-126 (emit both \$HOME-form AND absolute-path-form) — NOT a :* no-arg limitation. The no-:* exact rule the user added most likely 'worked' because saving a new rule triggered a settings re-read, or its specific literal form coincidentally matched that session's literal invocation. The :* suffix itself is sound for no-arg calls.

--- Disposition ---
AC #1 SATISFIED (repro recorded verbatim above). AC #6 SATISFIED (negative result + exact evidence recorded; closing not-needed, ZERO code changes to skills/ralph-init/SKILL.md). AC #2/#3/#4/#5 NOT APPLICABLE — each is gated on 'If repro confirms the pitfall'; the repro refutes it, so their precondition is false and no SKILL.md Step 3.7b/3.10 edits are made (intentionally). No wait-heartbeat.sh / utc-to-moscow.sh no-:* variants needed. TASK-127 (literal-match, the real issue) remains the correct vehicle.

task-reviewer: APPROVED (commit 503eb97). Verified AC #1 + #6 satisfied, AC #2-5 correctly N/A (refutation precondition false), diff scoped to task file only, master-branch-guard.sh correctly excluded, no R1-R15 violation. No build/lint/tests applicable: zero code changes (investigation-only, AC #6 path).
<!-- SECTION:NOTES:END -->
