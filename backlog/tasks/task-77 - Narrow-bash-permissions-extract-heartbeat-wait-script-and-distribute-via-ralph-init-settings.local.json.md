---
id: TASK-77
title: >-
  Narrow bash permissions: extract heartbeat-wait script and distribute via
  ralph-init settings.local.json
status: To Do
assignee: []
created_date: '2026-05-01 13:06'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Replaces the abandoned TASK-77. Goal: eliminate the 2nd permission prompt during /ralph-run without granting arbitrary bash execution via the over-broad Bash(bash:*) rule. Distribute the narrow rules through ralph-init so every project bootstrapped/upgraded with Ralph gets them.

## Background

- /ralph-run currently triggers two permission prompts: (1) the legitimate `nohup ./ralph.sh` launch with `dangerouslyDisableSandbox: true`, and (2) the heartbeat-poll for-loop whose leading token is `for` and matches no narrow allowlist rule.
- An earlier session added `Bash(bash:*)` to settings.local.json — too broad (allows arbitrary bash code execution).
- Earlier this session added two absolute-path rules to project `.claude/settings.json` (`preflight.sh` and brainstorm `resolve-rules.sh`); these aren't portable across users (paths reference $HOME of the original author).

## Design

### 1. New script: skills/ralph-run/scripts/wait-heartbeat.sh

Zero-arg script. Replaces the inline for-loop in ralph-run SKILL.md Step 4. Behavior:

```bash
#\!/usr/bin/env bash
set -euo pipefail

# Must be invoked from project root.
[ -d backlog ] || { echo "ERROR: must be invoked from project root (no backlog/ here)"; exit 2; }

for i in 1 2 3 4 5 6 7 8 9 10; do
  sleep 1
  if [ -f backlog/.ralph-heartbeat ]; then
    HB=$(stat -f %m backlog/.ralph-heartbeat 2>/dev/null || stat -c %Y backlog/.ralph-heartbeat 2>/dev/null)
    NOW=$(date +%s)
    AGE=$((NOW - HB))
    if [ "$AGE" -lt 15 ]; then
      echo "OK heartbeat age=${AGE}s after ${i}s"
      rm -f backlog/.ralph-launch.log
      exit 0
    fi
  fi
done

echo "FAIL no fresh heartbeat after 10s"
echo "--- launch log (last 20 lines) ---"
tail -20 backlog/.ralph-launch.log 2>/dev/null || echo "(launch log not created)"
echo "--- run log (last 20 lines) ---"
tail -20 backlog/.ralph-run.log 2>/dev/null || echo "(run log not created)"
exit 1
```

Make executable (chmod +x).

### 2. skills/ralph-run/SKILL.md Step 4 — replace inline poll with script invocation

Current (compound, no narrow allowlist):
```bash
for i in 1 2 3 4 5 6 7 8 9 10; do sleep 1; if [ -f backlog/.ralph-heartbeat ]; then ...; fi; done; echo "FAIL"; tail ...
```

New:
```bash
bash <absolute-path-to-skill-dir>/scripts/wait-heartbeat.sh
```

The absolute path is resolved by Claude (orchestrator) using the same SKILL.md-relative resolution pattern already used for preflight.sh.

ralph-run relays the script's stdout verbatim and uses exit code: 0 → Ralph launched (continue to Step 5 report); 1 → Ralph process died (already printed diagnostic tails); 2 → script invocation error.

### 3. skills/ralph-init/SKILL.md — generate settings.local.json rules at init/upgrade

Add a new sub-step in Step 3.7 (`.claude/settings.json`, `.claude/settings.local.json`, `.claude/agents/task-reviewer.md`):

After writing `templates/settings.local.json` to `.claude/settings.local.json`, MERGE the following rules into `permissions.allow` (idempotent — dedupe by exact-string match, don't touch unrelated entries):

- `Bash(bash <RESOLVED_HOME>/.claude/skills/ralph-run/scripts/preflight.sh:*)`
- `Bash(bash <RESOLVED_HOME>/.claude/skills/ralph-run/scripts/wait-heartbeat.sh:*)`

Where `<RESOLVED_HOME>` is the user's actual home directory at install time, resolved via `echo \"$HOME\"` (NOT a literal `$HOME` or `~` — Claude Code permission patterns are literal-match).

Implementation hint: use `jq` for the merge, e.g.:
```bash
RULE1=\"Bash(bash $HOME/.claude/skills/ralph-run/scripts/preflight.sh:*)\"
RULE2=\"Bash(bash $HOME/.claude/skills/ralph-run/scripts/wait-heartbeat.sh:*)\"
jq --arg r1 \"$RULE1\" --arg r2 \"$RULE2\" '
  .permissions.allow = ((.permissions.allow // []) + [$r1, $r2] | unique)
' .claude/settings.local.json > .claude/settings.local.json.new && mv ...
```

### 4. Upgrade-mode parity

The same merge logic must run when ralph-init is invoked in upgrade mode (`/ralph-init upgrade` or 'update ralph files' triggers). Existing projects bootstrapped before this task get the new rules on next upgrade.

### 5. Cleanup of THIS project (not part of ralph-init template)

After the task is implemented, run a one-shot cleanup against this Ralph repo's own settings:

- `.claude/settings.local.json`: remove `Bash(bash:*)` line (over-broad).
- `.claude/settings.json`: remove the two absolute-path rules added earlier this session: `Bash(bash /Users/paul/.claude/skills/ralph-run/scripts/preflight.sh:*)` and `Bash(bash /Users/paul/.claude/plugins/cache/umputun-cc-thingz/brainstorm/2.2.1/scripts/resolve-rules.sh:*)`. They aren't portable (reference your home dir) and don't belong in committed project settings.
- After cleanup, run `/ralph-init upgrade` on this project to regenerate the user-correct settings.local.json rules.

## Smoke tests

1. Fresh `/ralph-run` (no watch) — exactly ONE permission prompt fires (the dangerous-mode launch). Heartbeat-wait auto-allows because its leading token+path matches the new narrow rule.
2. Fresh `/ralph-run watch=2m` — same: only one prompt.
3. Force a launch failure (e.g., make ralph.sh non-executable temporarily) — wait-heartbeat.sh exits 1 with FAIL message + log tails, surfaced verbatim by ralph-run.
4. Run `/ralph-init` in a fresh test directory — verify generated settings.local.json contains the two narrow rules with the user's actual home path resolved.
5. Run `/ralph-init upgrade` on a test project that has an existing settings.local.json with custom rules — verify custom rules preserved, the two new rules added if missing, no duplicates.
6. Regression: existing ralph-run preflight invocation continues to auto-allow under the new settings.local.json rule (project-level rule was removed in step 5 cleanup).

## Out of scope

- Brainstorm `resolve-rules.sh` rule — third-party plugin, not ralph-init's concern. User adds manually if desired.
- Changing ralph.sh.
- Refactoring preflight.sh.
- Bundling scripts into project (option A from brainstorm — explicitly rejected in favor of B).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 skills/ralph-run/scripts/wait-heartbeat.sh exists, executable, zero-arg, polls 10x1s, freshness <15s threshold
- [ ] #2 wait-heartbeat.sh fails fast with ERROR if invoked outside a project (no backlog/ dir)
- [ ] #3 wait-heartbeat.sh on success: prints OK heartbeat line, removes backlog/.ralph-launch.log, exits 0
- [ ] #4 wait-heartbeat.sh on failure: prints FAIL line plus tails of backlog/.ralph-launch.log and backlog/.ralph-run.log (or 'not created'), exits 1
- [ ] #5 skills/ralph-run/SKILL.md Step 4 replaces the inline for-loop with bash <abs-path>/scripts/wait-heartbeat.sh invocation
- [ ] #6 skills/ralph-init/SKILL.md Step 3.7 merges two narrow rules into settings.local.json permissions.allow with /Users/paul resolved at install time
- [ ] #7 Merge logic is idempotent: re-running ralph-init does not duplicate rules in settings.local.json
- [ ] #8 Upgrade mode applies the same merge so existing projects pick up the new rules
- [ ] #9 This project's .claude/settings.local.json has Bash(bash:*) removed
- [ ] #10 This project's .claude/settings.json has the two absolute-path rules (preflight.sh, brainstorm resolve-rules.sh) removed
- [ ] #11 After cleanup + ralph-init upgrade run on this project, /ralph-run produces only one permission prompt (the nohup launch)
- [ ] #12 Smoke test: forced launch failure shows FAIL message and log tails surfaced through ralph-run
- [ ] #13 Smoke test: ralph-init in a fresh test dir generates settings.local.json with the user's actual home path resolved (no literal $HOME or ~)
<!-- AC:END -->
