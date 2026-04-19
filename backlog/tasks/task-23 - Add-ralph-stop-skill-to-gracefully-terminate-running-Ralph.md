---
id: TASK-23
title: Add ralph-stop skill to gracefully terminate running Ralph
status: Done
assignee:
  - '@claude'
created_date: '2026-04-19 10:20'
updated_date: '2026-04-19 19:08'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Currently there is no skill to stop a running Ralph loop. Users must manually read PID from backlog/.ralph-status.json and kill it. This is friction, especially for users who launched Ralph and want to stop it without leaving Claude Code.

Add skills/ralph-stop/SKILL.md that:
1. Reads PID from backlog/.ralph-status.json
2. Verifies the process is alive (kill -0 $PID)
3. Asks user for confirmation (with current iteration / task info)
4. Sends SIGTERM to allow graceful shutdown (so trap handlers run, status file is updated to 'stopped')
5. Waits up to 10s for the process to exit; sends SIGKILL if it doesn't
6. Reports final status to user

Trigger phrases: 'stop ralph', 'kill ralph', 'ralph stop'.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-stop/SKILL.md exists with proper frontmatter (name, description, triggers)
- [x] #2 Skill reads PID from backlog/.ralph-status.json and validates process is alive
- [x] #3 Skill confirms with user before killing (showing current iteration/task)
- [x] #4 Skill sends SIGTERM first, falls back to SIGKILL after 10s
- [x] #5 If no Ralph is running, skill reports cleanly without error
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Brainstorm Design (2026-04-19)

Two-part design: fix ralph.sh trap to propagate SIGTERM to children + add ralph-stop skill.

## Part 1: ralph.sh trap fix (prerequisite)

### Problem
Current trap `_ralph_interrupt` (lines 199-204) exits bash but orphans child processes (timeout, claude). Killing ralph.sh does not actually stop the AI agent's work.

### Capture RUN_LOG tee PID (modify ralph.sh:303)

```bash
exec > >(tee -a "$RUN_LOG") 2>&1
RUN_LOG_TEE_PID=$\!
```

### Update trap handler (modify ralph.sh:199-204)

```bash
_ralph_interrupt() {
  EXIT_REASON="interrupted"
  # Kill direct children (timeout/claude) but preserve RUN_LOG tee so final log flushes
  for pid in $(pgrep -P $$ 2>/dev/null); do
    if [[ "$pid" \!= "${RUN_LOG_TEE_PID:-}" ]]; then
      kill -TERM "$pid" 2>/dev/null || true
    fi
  done
  _update_status "failed" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "130"
  show_summary "interrupted"
  exit 130
}
```

**Scope minimization:** keep state="failed" on interrupt. Not introducing new state name. EXIT_REASON="interrupted" is already shown separately in summary output.

## Part 2: skills/ralph-stop/SKILL.md

Full skill content:

```markdown
---
name: ralph-stop
description: "Stop a running Ralph autonomous agent. Sends SIGTERM for graceful shutdown, falls back to SIGKILL after 10s. Triggers on: stop ralph, kill ralph, ralph stop."
---

# Ralph Stop

## Step 1: Read status file
Read backlog/.ralph-status.json. If missing, output 'No Ralph has been run yet (no status file found).' and stop.

## Step 2: Verify state
Parse state field. If state \!= "running", output 'Ralph is not running (state: <state>). Nothing to stop.' and stop.

## Step 3: Verify PID alive
Run kill -0 $PID 2>/dev/null. If the process is not alive, output 'Ralph PID <pid> not found (probably crashed). Status file is stale.' and stop.

## Step 4: Confirm with user
Show current iteration/task from status file:
'Stop Ralph (PID <pid>) at iteration <N> of <max>, current task: <task>? [y/N]'
If not confirmed, stop without action.

## Step 5: Graceful shutdown
Send SIGTERM: kill -TERM $PID
Poll for exit (up to 10 attempts at 1s intervals):
  for i in 1..10: if \! kill -0 $PID 2>/dev/null; then break; fi; sleep 1

## Step 6: Force if needed
If still alive after 10s: kill -KILL $PID; sleep 1; verify dead.

## Step 7: Report
Re-read status file to get final state. Output:
'Ralph stopped (PID <pid>). Final state: <state>.'
```

## Test coverage

New file: tests/integration/interrupt-trap.bats

1. **Trap propagates SIGTERM to children** — launch ralph.sh with long-running mock tool, send SIGTERM to ralph.sh, verify mock tool's PID is no longer alive within 2s
2. **RUN_LOG tee survives interrupt long enough to flush** — same setup, verify backlog/.ralph-run.log contains expected output up to the interrupt point
3. **Status file reflects interruption** — after SIGTERM, backlog/.ralph-status.json has state="failed", exit_code=130, and errors/summary indicates 'interrupted'

## Acceptance criteria (replaces originals)

- AC1: skills/ralph-stop/SKILL.md exists with proper frontmatter (name, description, triggers) and the 7 steps above
- AC2: ralph.sh trap handler propagates SIGTERM to children (excluding RUN_LOG tee) so claude subprocess terminates
- AC3: Skill reads PID from backlog/.ralph-status.json, validates process is alive, confirms with user
- AC4: SIGTERM first, SIGKILL fallback after 10s
- AC5: If no Ralph running (missing file, state \!= running, or PID dead), skill reports cleanly without error
- AC6: New interrupt-trap.bats test verifies children are killed on SIGTERM and RUN_LOG retains content

Plan: Implement per the brainstorm design. Part 1: fix ralph.sh trap to propagate SIGTERM to children (capture tee PID, update _ralph_interrupt). Part 2: create skills/ralph-stop/SKILL.md. Part 3: add interrupt-trap.bats tests.

Commit: `704df99` - task-23: Add ralph-stop skill and SIGTERM child propagation

Implemented ralph-stop skill (skills/ralph-stop/SKILL.md) with 7-step shutdown flow. Added _kill_children helper in ralph.sh trap handler for SIGTERM propagation to child process groups. Added RUN_LOG_TEE_PID capture to preserve log output during interrupts. 3 integration tests in tests/integration/interrupt-trap.bats.
<!-- SECTION:NOTES:END -->
