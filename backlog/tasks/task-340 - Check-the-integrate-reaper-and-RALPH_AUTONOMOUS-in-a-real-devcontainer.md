---
id: TASK-340
title: Check the integrate reaper and RALPH_AUTONOMOUS in a real devcontainer
status: To Do
assignee: []
created_date: '2026-11-07T21:35:00Z'
updated_date: '2026-11-08T15:02:00Z'
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
- [ ] #1 (host) After integrate times out in a real devcontainer, the grep finds no tagged process; the command and its output are recorded in the notes
- [ ] #2 (host) Inside a real devcontainer run, RALPH_AUTONOMOUS=1 is set, SHARED_BACKLOG_HOLDER and RALPH_RUN_LOCK_TOKEN carry the host run's values (the same --remote-env path, so far only tested against a fake devcontainer), and backlog task create is refused in an enforcing clone; recorded in the notes
<!-- AC:END -->
