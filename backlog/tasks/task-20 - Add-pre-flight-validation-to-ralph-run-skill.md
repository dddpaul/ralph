---
id: TASK-20
title: Add pre-flight validation to ralph-run skill
status: To Do
assignee: []
created_date: '2026-04-19 10:19'
updated_date: '2026-04-19 13:17'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
skills/ralph-run/SKILL.md currently launches ralph.sh and only catches 'process exited immediately' as a failure mode. Users get no diagnostic about why — they must dig through backlog/.ralph-run.log manually.

Fix: in skills/ralph-run/SKILL.md step 3 (Validate Preconditions), add:
- 'test -x ./ralph.sh' (script is executable)
- 'bash -n ./ralph.sh' (script has valid bash syntax)
On failure, report which check failed with the actual error output.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Skill validates ralph.sh is executable before launching
- [ ] #2 Skill runs 'bash -n ./ralph.sh' syntax check before launching
- [ ] #3 Failed validation reports the specific check that failed and its error output
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Brainstorm Design (2026-04-19)

Scope expanded from original task description. Both static checks AND output capture (latter more impactful).

## Changes to skills/ralph-run/SKILL.md

### Step 3.4 (new) — ralph.sh integrity checks

Add after existing Step 3.3 (devcontainer CLI check):

```bash
# 3.4 ralph.sh integrity
if [[ \! -x "$RALPH_PATH" ]]; then
  echo 'Error: ralph.sh is not executable. Run: chmod +x ./ralph.sh'
  exit 1
fi

if \! bash -n "$RALPH_PATH" 2>/tmp/ralph-syntax-err; then
  echo 'Error: ralph.sh has syntax errors:'
  cat /tmp/ralph-syntax-err
  exit 1
fi
```

### Step 4 — Capture launch output

Change the existing nohup line:

```bash
# Before
nohup bash -c "$RALPH_CMD" > /dev/null 2>&1 & disown

# After
LAUNCH_LOG='backlog/.ralph-launch.log'
nohup bash -c "$RALPH_CMD" > "$LAUNCH_LOG" 2>&1 & disown
RALPH_PID=$\!
```

**Rationale:** ralph.sh:303 does `exec > >(tee -a "$RUN_LOG") 2>&1` but only kicks in *inside* the script. Errors before that line (arg parsing, `command -v backlog` check at ralph.sh:207-208) never reach RUN_LOG. The launch log captures pre-exec errors.

### Step 4 (continued) — On successful launch, delete launch log

After verifying `kill -0 $RALPH_PID` succeeds:

```bash
rm -f "$LAUNCH_LOG"
```

Keeps backlog/ clean. The log only survives when launch failed (when it has diagnostic value).

### Step 5 — Diagnostic on early-exit failure

Change the 'process exited immediately' error to include tails of both logs:

```
Error: Ralph process exited immediately.

--- Last 20 lines of launch output (backlog/.ralph-launch.log) ---
<tail -20 of LAUNCH_LOG>

--- Last 20 lines of run log (backlog/.ralph-run.log, if exists) ---
<tail -20 of backlog/.ralph-run.log if exists, else 'not created'>

For full output, inspect both files.
```

## Also update

**.gitignore:** add `backlog/.ralph-launch.log` (session state, should not be committed)

## Non-goals

- Do NOT add RALPH_PATH resolution logic change — still uses existing Step 2 logic (./ralph.sh or scripts/ralph/ralph.sh)
- Do NOT modify ralph.sh itself — all changes confined to skills/ralph-run/SKILL.md and .gitignore
<!-- SECTION:NOTES:END -->
