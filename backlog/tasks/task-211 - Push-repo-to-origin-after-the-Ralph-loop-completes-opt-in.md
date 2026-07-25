---
id: TASK-211
title: Push repo to origin after the Ralph loop completes (opt-in)
status: Done
assignee: []
created_date: '2026-07-25 09:31'
updated_date: '2026-07-25 09:57'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Handoff from control-gateway slice-3 mesh E2E (TASK-31). Source: /Users/paul/Private/Projects/ai/control-gateway@4fe59f1

WHY: the control-gateway cross-project mesh needs an upstream Ralph run to PUBLISH its merges as okf canon. okf serves owner 'ralph' from the github remote (https://github.com/dddpaul/ralph.git @master), so 'published as canon' == the merge reaching origin/master. Today the orchestrator's loop merges task branches to LOCAL master only and never pushes, so okf never sees the merge and downstream mesh members never unblock. Give the ORCHESTRATOR a first-class 'push after the loop is done' capability so the mesh's upstream producer publishes canon automatically.

WHAT: after the autonomous loop finishes, push the repo's master ref to origin BY DEFAULT. Push only when BOTH (a) an 'origin' remote is registered, and (b) the loop actually advanced master (task(s) merged) — snapshot 'git rev-parse <master-ref>' before the loop and compare after. If no origin remote is registered, skip cleanly (no push, no error). Provide an opt-out flag/env for runs that must not push. Surface a push failure loudly (non-zero exit / logged error), never swallow it.

OWNER DECISION (2026-07-25): diverges from the source handoff's opt-in framing. This repo's owner requires push to be DEFAULT-ON, gated on 'origin' being registered — because this repo IS the mesh's canon producer, so every advancing run should publish.

Merge location: performed by the agent per CLAUDE.md Task Lifecycle step 6 (git checkout master && git merge <branch>), NOT in the orchestrator (loop.py never merges). Master ref: master. Push egress: host SSH works; devcontainer firewall allows SSH:22 + GitHub IP ranges.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Push-on-complete is ENABLED BY DEFAULT; an opt-out CLI flag and/or env var disables it
- [x] #2 When enabled, after the loop finishes it pushes the master ref to origin (git push origin <master-ref>)
- [x] #3 Push runs only when an 'origin' remote is registered; with no origin remote, nothing is pushed and no error is raised
- [x] #4 Push runs only when the loop actually advanced master (pre/post rev-parse differ); a no-op loop pushes nothing
- [x] #5 A push failure (when a push is attempted) is surfaced (non-zero exit / logged error), never silently swallowed
- [x] #6 With the opt-out flag/env set, behavior is unchanged and nothing is pushed
- [x] #7 Tests cover: default-enabled-and-pushed, opt-out-no-push, no-origin-no-push, no-op-loop-no-push, and push-failure-surfaced
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: ralph.sh is a thin shim (execs Python orchestrator); the loop lives in plugins/ralph/skills/ralph-run/scripts/ralph/loop.py. Approach: (1) new module ralph/push.py — push_enabled(cli_push) resolves opt-out (--no-push CLI OR truthy RALPH_NO_PUSH env), current_rev()/has_origin_remote() git helpers, maybe_push_after_loop() gates on enabled AND origin-registered AND master-advanced then runs 'git push origin master', surfacing failure via stderr + non-zero PushOutcome.exit_code. (2) args.py — add --no-push (dest=push, store_false, default True) + push:bool=True field. (3) loop.py run() — snapshot rev_before pre-loop, call maybe_push_after_loop after _finalize, OR a push failure into exit_code. (4) tests: test_push.py (hermetic tmp git repos + bare origin cover all 5 AC#7 scenarios) + test_orchestrator_args.py flag test. (5) README CLI Options + env var docs. No bash/R11 parity (orchestrator is single source of truth).

Commit: `e7806e2` - task-211: push master to origin after an advancing loop

Implemented push-on-complete in the Python orchestrator (single source of truth; ralph.sh is a thin shim). New ralph/push.py: push_enabled() resolves opt-out (--no-push CLI or truthy RALPH_NO_PUSH env), has_origin_remote()/current_rev() helpers, maybe_push_after_loop() gates on enabled AND origin-registered AND master-advanced (pre/post git rev-parse), runs 'git push origin master', surfaces failure via stderr + non-zero PushOutcome.exit_code. loop.py snapshots master before the loop and pushes after _finalize, carrying a push failure into the exit code without masking a failing/interrupted loop. args.py adds --no-push (default push=True). Docs: README CLI row + RALPH_NO_PUSH env + 'Publishing to origin' section. Tests: test_push.py (hermetic work-repo + bare origin cover all 5 AC#7 scenarios), test_loop_push.py (loop wiring), test_orchestrator_args.py (flag). Gate green: ruff clean, pyright 0 errors on scripts, pytest 346 passed (+29). task-reviewer verdict: APPROVED. No R5 (no shell changes) / R11 (orchestrator excluded from mirror set) concerns.
<!-- SECTION:NOTES:END -->
