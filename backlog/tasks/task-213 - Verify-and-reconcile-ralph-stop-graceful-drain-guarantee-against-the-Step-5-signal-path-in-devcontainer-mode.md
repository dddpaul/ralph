---
id: TASK-213
title: >-
  Verify and reconcile ralph-stop graceful-drain guarantee against the Step 5
  signal path in devcontainer mode
status: Done
assignee: []
created_date: '2026-07-26 16:16'
updated_date: '2026-08-01 08:16'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

TASK-210 (Done) documented `ralph-stop` as a **graceful drain**: the in-flight in-container agent finishes its task and merges cleanly, then the loop halts because no orchestrator remains. But that guarantee's *mechanism* was never verified against the **documented Step 5 signal path**. Step 5 sends `pkill -TERM -P <pid>` (SIGTERM to the orchestrator's direct children) and `kill -TERM <pid>` (SIGTERM to the orchestrator) — and separately, loop.py's `_SignalInstaller` forwards SIGTERM to the active tool subprocess's process group (the TASK-160 parity closer). In `--devcontainer` mode the orchestrator's child / active subprocess is the **host-side proxy** (`node devcontainer exec …` → `docker exec …`) that bridges stdio into the container. So the documented stop SIGTERMs that proxy.

Open question: does SIGTERMing the host proxy let the in-container agent drain to a clean merge (plausible — the container-side pipe endpoint is held by the docker daemon/shim, not the client), or does it abort the agent via severed stdio (EOF / SIGPIPE), leaving a partial diff? TASK-210's "observed live" note does not record which signal path it used, so the guarantee is asserted but not verified for the Step 5 path. This task verifies it empirically and, if the guarantee does not hold under the documented path, fixes the mechanism so it does — without regressing the TASK-160 SIGTERM-forwarding intent for non-devcontainer (host-process) runs.

Evidence from the source project (control-gateway): a **SIGKILL of the orchestrator alone** (untrappable → `_SignalInstaller` handler never runs → no forwarding → the host proxy reparents to init with its stdio pipe intact) reliably let an in-flight task run to completion and merge cleanly. The behavior of the trappable SIGTERM path (which *does* forward to the proxy) is what is unverified.

## Scope

In scope:
- Empirically verify, on a real `--devcontainer` Ralph run, whether issuing the documented ralph-stop Step 5 signals mid-iteration lets the in-flight in-container agent finish and merge its task with no dirty working tree. Record the observed git state and which signals were sent in the task notes.
- If the in-flight agent does NOT drain cleanly under the documented Step 5 path, fix the mechanism (ralph-stop Step 5 and/or loop.py `_SignalInstaller`) so the documented clean-drain guarantee holds in `--devcontainer` mode — scoping any change to devcontainer runs only.
- If the agent DOES drain cleanly under the documented path, annotate `plugins/ralph/skills/ralph-stop/SKILL.md` to state the verified signal path explicitly, so the guarantee and the exact Step 5 commands are demonstrably consistent (not just asserted).

Out of scope:
- Changing non-devcontainer (host-process) stop behavior, or the TASK-160 SIGTERM-forwarding for host-process runs.
- Re-documenting the graceful-drain concept that TASK-210 already added (that section stays; only reconcile/annotate it against the verified mechanism).
- Adding any force-kill of the in-container agent (`devcontainer exec … pkill claude`) — that corrupts in-flight work and is explicitly the anti-pattern TASK-210 warns against.
- Reordering or reworking unrelated Step sections of the skill.

## Files

- `plugins/ralph/skills/ralph-stop/SKILL.md` (exists) — the "Behavior: graceful drain" preamble states the clean-drain guarantee (~line 19); Step 5 sends `pkill -TERM -P <pid>` (~line 103) then `kill -TERM <pid>` (~line 109). This is the doc-vs-mechanism pair to reconcile.
- `plugins/ralph/skills/ralph-run/scripts/ralph/loop.py` (exists) — `_SignalInstaller` (~line 554) installs SIGINT/SIGTERM handlers that "forward the signal to the active tool subprocess's process group" (docstring ~line 555-566; handler install ~line 585; `set_active_subprocess` ~line 604). This forwarding is the mechanism that SIGTERMs the host-side proxy in devcontainer mode.

## Source

Source: /Users/paul/Private/Projects/ai/control-gateway@aabbe7c9d65e
Related destination task (Done, context — do NOT redo): TASK-210 (documented the graceful-drain behavior in the same SKILL.md).

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, build command, or observed git state recorded in notes — not "works correctly").
3. All dependencies in the task's frontmatter are status=Done (TASK-210 is Done; confirm).
4. Out-of-scope items are not accidentally pulled in by ambiguous AC (do NOT alter non-devcontainer stop behavior; do NOT add a force-kill).

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A live --devcontainer Ralph run is stopped mid-iteration using ONLY the documented ralph-stop Step 5 signals (pkill -TERM -P <pid> then kill -TERM <pid>); the implementation notes record which signals were sent, the in-flight task ID, and the observed post-stop git state (branch, whether the task merged, whether the working tree was clean)
- [x] #2 The notes state a clear verdict: under the documented Step 5 path the in-flight in-container agent EITHER drained to a clean merge with no dirty working tree, OR it did not (with the failure mode described)
- [x] #3 If the agent did NOT drain cleanly under the Step 5 path: plugins/ralph/skills/ralph-stop/SKILL.md and/or plugins/ralph/skills/ralph-run/scripts/ralph/loop.py are changed so the documented clean-drain guarantee holds in --devcontainer mode, with the change scoped to devcontainer runs — N/A: clean drain was verified under the Step 5 path, so the AC#4 (annotate) branch was taken and no mechanism fix was required
- [x] #4 If the agent DID drain cleanly under the Step 5 path: plugins/ralph/skills/ralph-stop/SKILL.md is annotated to state the verified signal path so the graceful-drain guarantee and the Step 5 commands are demonstrably consistent
- [x] #5 Non-devcontainer (host-process) stop behavior and the TASK-160 SIGTERM-forwarding in loop.py _SignalInstaller are unchanged for host-process runs (verified by inspection and by the full suite staying green)
- [x] #6 No force-kill of the in-container agent is introduced (grep of the skill and scripts shows no 'devcontainer exec' + 'pkill'/'kill' targeting the in-container claude/opencode)
- [x] #7 Lint green: uv run ruff check .
- [x] #8 Tests green: uv run pytest
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan (interactive experiment): (1) create synthetic throwaway guinea-pig task; (2) launch a --devcontainer Ralph run on it with --no-push (avoid publishing throwaway); (3) once the in-container agent is mid-iteration (branch created / WIP), issue ONLY the documented ralph-stop Step 5 signals: pkill -TERM -P <orchestrator-pid> then kill -TERM <orchestrator-pid>; (4) observe + record post-stop git state (branch, merged?, tree clean?); (5) verdict -> clean drain: annotate ralph-stop SKILL.md with verified path; aborted: fix mechanism scoped to devcontainer; (6) cleanup guinea-pig.

Empirical verification (interactive, 3 --devcontainer --no-push guinea-pig runs on synthetic throwaway tasks):

- Runs 1 & 2 (TASK-216, TASK-217): trivial one-line tasks completed the full lifecycle (branch → file → lint/test → review → merge → Done) in ~4-6 min, faster than an observe-then-fire round-trip could catch mid-iteration → null result (no signal ever landed). Kept as timing calibration.
- Run 3 (TASK-218): atomic detect-and-fire. The instant the host-side proxy `node devcontainer exec … claude --print` appeared (~4s in, state=running, master unchanged, branch not yet created), issued ONLY the documented Step 5 signals against the status-file PID: `pkill -TERM -P 42144` (rc=0) then `kill -TERM 42144` (rc=0).

Observed post-fire (host):
- Orchestrator 42144 exited 2s after fire; status.json state=failed.
- The entire host-side proxy chain died: `node devcontainer exec … claude` (36562-analog) + both `docker exec -i` clients — all gone.
- master unchanged; no task-218 branch yet; probe file absent.

Observed inside the container (docker exec … ps) — the decisive evidence:
- The in-container agent `claude --model … --print` was STILL ALIVE, PID 710962, reparented to PPID 0 (container init) — its `docker exec -i` parent was gone but the agent (separate PID namespace) survived the severed stdio.
- It kept working with NO orchestrator alive: created branch task-218, committed design/drain-probe-3.md, then (watched over ~180s) marked the task Done (2nd commit), ran `git checkout master && merge --no-ff && branch -d`. master advanced 55c7f23 → 3d8346a; branch deleted; working tree clean (only the unrelated experimenter task-213 edit).

VERDICT (AC #2): Under the documented Step 5 signal path the in-flight in-container agent DRAINED TO A CLEAN MERGE — no dirty working tree, no partial diff. The Step 5 pkill/kill + loop.py _SignalInstaller SIGTERM-forwarding reach only the host-side proxy (node devcontainer exec → docker exec -i, no -t/--sig-proxy); the PID-namespace-isolated agent is untouched and completes. AC #4 path taken (annotate SKILL.md); AC #3 (mechanism fix) NOT needed. Throwaway guinea-pig commits/files reset off master (master realigned to origin 5b3c1a1); TASK-216/217/218 discarded.

Commit: `833fe51` - task-213: annotate ralph-stop with the verified graceful-drain signal path (Step 5 kills only the host-side devcontainer-exec/docker-exec proxy; the PID-isolated in-container agent, orphaned with PPID 0, drains to a clean merge)

Deliverable: SKILL.md '### Verified signal path (TASK-213)' annotation (commit on task-213 branch). Review: ralph:task-reviewer → APPROVED (doc-only, 14 lines; loop.py untouched per AC#5; no force-kill added per AC#6; reviewer PPID nit reconciled to observed PPID 0). Final gate green: ruff clean, pytest 346 passed. AC#3 N/A (clean-drain verdict → AC#4 branch taken).
<!-- SECTION:NOTES:END -->
