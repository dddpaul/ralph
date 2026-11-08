---
id: TASK-340
title: Check the integrate reaper and RALPH_AUTONOMOUS in a real devcontainer
status: In Progress
assignee: []
created_date: '2026-11-07T21:35:00Z'
updated_date: '2026-11-08T16:58:00Z'
labels:
  - feature:plugin-delivered-project-files
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Why: the integrate timeout reaper (US-019) and the RALPH_AUTONOMOUS environment of the autonomous-create guard (US-022) are tested only against a fake devcontainer. These checks need a host with Docker and a real --devcontainer run, so they are interactive host checks, not Ralph work.

Reaper (TASK-313 follow-up): from a --devcontainer run in an enforcing test clone, run integrate with hanging checks (for example checks 'sleep 600') and RALPH_INTEGRATE_TIMEOUT=60. Then confirm no process tagged RALPH_INTEGRATE_TAG survives in the container:

    docker exec <id> sh -c 'grep -l RALPH_INTEGRATE_TAG /proc/[0-9]*/environ'

Guard: during an autonomous --devcontainer run in an enforcing test clone, confirm RALPH_AUTONOMOUS=1 is set inside the container and that backlog task create is refused there.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 (host) After integrate times out in a real devcontainer, the grep finds no tagged process; the command and its output are recorded in the notes
- [x] #2 (host) Inside a real devcontainer run, RALPH_AUTONOMOUS=1 is set, SHARED_BACKLOG_HOLDER and RALPH_RUN_LOCK_TOKEN carry the host run's values (the same --remote-env path, so far only tested against a fake devcontainer), and backlog task create is refused in an enforcing clone; recorded in the notes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan (macOS host, interactive, 2026-11-08): one real --devcontainer Ralph run of the installed plugin (0.25.11, user scope) in a throwaway enforcing project: a bare origin plus a clone with .claude/ralph.json {"sharedBacklog": true, "checks": "sleep 600"}, shared-backlog.sh enable --holder @tp340-mac, and this repo's .devcontainer. The project's only task tells the agent inside the container to write RALPH_AUTONOMOUS and SHARED_BACKLOG_HOLDER to a probe file, to compare RALPH_RUN_LOCK_TOKEN with the token in .git/shared-backlog-run.lock/owner (recording only match or no match), and to try backlog task create (AC #2). The run is launched with RALPH_INTEGRATE_TIMEOUT=60, so its own publish through integrate times out while the checks hang in the container. A host loop runs docker exec grep for RALPH_INTEGRATE_TAG every 5 s through the run, as a positive control during the checks and as the AC #1 check after the timeout.

Host check (macOS, Docker 29.2.1, devcontainer CLI 0.90.0, installed plugin 0.25.11 at user scope, 2026-11-08). Test project: a bare origin and one clone under ~/.cache/ralph-tp340. On this Mac, Docker only bind-mounts paths under /Users, so neither the session scratchpad nor $TMPDIR works as a devcontainer workspace. The clone carries the ralph-init ralph.sh and shared-backlog.sh shims and this repo's .devcontainer. Its .claude/ralph.json is {"sharedBacklog": true, "checks": "sleep 600"}. After shared-backlog.sh enable --holder @tp340-mac, ralph.sharedBacklog is true and the plugin pre-push shim is installed. Each run is RALPH_INTEGRATE_TIMEOUT=60 ./ralph.sh --tool claude --model claude-opus-5-5 --effort medium --timeout 15 --devcontainer --tasks <N> 1, launched detached the way /ralph-run does it.

AC #2, run 1 (TASK-1, 16:50:50Z to 16:52:41Z). The run printed 'holding the shared-backlog run lock as @tp340-mac' and claimed TASK-1, pushing 8651283 'task-1: claim for @tp340-mac'. The agent inside the container wrote probe/env.txt:
  RALPH_AUTONOMOUS=1
  SHARED_BACKLOG_HOLDER=@tp340-mac
  RALPH_RUN_LOCK_TOKEN: set, equal to the run lock owner token
  DEVCONTAINER=true
The token check compared the variable with the token= line of .git/shared-backlog-run.lock/owner, the lock the host run holds; only the result was recorded. The agent's backlog task create "Probe follow-up that must not be created" was refused with: 'PreToolUse:Bash hook error: [<installPath 0.25.11>/hooks/autonomous-create-guard.sh]: BLOCKED: backlog task create during an autonomous run: this clone enforces the shared-backlog protocol (git config ralph.sharedBacklog true), and an autonomous run must not allocate a task or draft ID. ...'. probe/tasks.txt lists only task-1, so no task was created.

AC #1, the reaper. In run 1 the publish through integrate (checks in the devcontainer) ran past 60 s and printed:
  killed 2 check process(es) left in the devcontainer
  ERROR: shared-backlog integrate ran past its 60s timeout (RALPH_INTEGRATE_TIMEOUT); killed its process groups.
  killed 0 check process(es) left in the devcontainer
  State left as is, not reset: local master at 881b45b22; 1 ahead / 0 behind origin/master.
The run ended with exit 124. With a 60 s timeout the script's own deadline is also 60 s, so the first 'killed 2' is the script's SHARED_BACKLOG_CHECKS_KILL running after the orchestrator's SIGTERM, and the second line is the orchestrator's own reap, which found nothing left.

My host watcher in run 1 was invalid and is not evidence. It ran the grep as docker exec -u root, and the container's root cannot read the node user's /proc/<pid>/environ: a self-test got 'Permission denied', hidden by 2>/dev/null. The task's command, run as the default user, does find a tagged process. I fixed the watcher, which then found a tagged self-test sleep, and ran a second run.

The next run first refused with 'local master has diverged from origin/master; run integrate first', which is correct after a publish that timed out. I ran SHARED_BACKLOG_CHECKS=true bash scripts/shared-backlog.sh integrate by hand, which pushed 048ad00, and added TASK-2 with shared-backlog.sh create.

Run 2 (TASK-2, 16:55:47Z to 16:57:17Z, exit 124) printed the same four lines: killed 2, timeout, killed 0, state left as is. The watcher, running docker exec <id> sh -c 'grep -l RALPH_INTEGRATE_TAG /proc/[0-9]*/environ' every 5 s, logged the tagged checks from 19:56:20 to 19:57:12 local time, PIDs 2098 'sh -c sleep 600' and 2104 'sleep 600', and none from 19:57:17 on. After the run, the task's exact command docker exec 6c2aecaf6832 sh -c 'grep -l RALPH_INTEGRATE_TAG /proc/[0-9]*/environ' printed nothing and exited 1.
<!-- SECTION:NOTES:END -->
