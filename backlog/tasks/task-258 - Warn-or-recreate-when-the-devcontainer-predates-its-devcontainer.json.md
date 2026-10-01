---
id: TASK-258
title: Warn or recreate when the devcontainer predates its devcontainer.json
status: To Do
assignee: []
created_date: '2026-10-01 07:12'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

`devcontainer up` reuses any existing container, and `devcontainer.json` mount and config changes apply only at container **creation**. `start_devcontainer` already documents this (`plugins/ralph/skills/ralph-run/scripts/ralph/devcontainer.py:27-30`, TASK-237) and `rebuild=True` exists to force a fresh one — but nothing detects the stale case, so a reused container silently ignores the config it is supposed to be running under. The operator gets `Devcontainer is ready.` either way.

Measured on this repo, 2026-10-01:

| | |
|---|---|
| container created | `2026-09-27T13:13:06Z`, "Up 3 days" |
| `.devcontainer/devcontainer.json` last changed | `2026-09-27T16:40:22Z` (TASK-251, added `UV_VERSION`) |
| single-file overlay present inside it | **no** — `grep -c '/workspace/.claude/settings.local.json' /proc/self/mountinfo` returns 0 |
| what the container reads at that path | the host file, `sandbox.enabled: true` |

The missing mount is the one from TASK-239 whose whole purpose is forcing `sandbox.enabled: false` inside the container, because bwrap cannot create mount namespaces on Docker Desktop macOS. That override has not been in effect for three days. Runs kept succeeding because Ralph launches `claude --dangerously-skip-permissions` in the container, so the container has been running in a configuration nobody designed or tested rather than visibly failing. That is the bad shape: silent drift, not a crash.

Discovered sideways. TASK-257's AC asked the agent to update the gitignored live `.claude/settings.local.json`; that should have been impossible from inside the container, and it succeeded, because the overlay was not there.

## Why it matters beyond this machine

The planned fleet upgrade sweep pushes a new `devcontainer.json` to many projects. On every project with an existing container, the new config will be silently ignored until that container is recreated, and nothing will say so. A project can report a clean upgrade and still run the old configuration indefinitely.

## Direction

In `start_devcontainer`, before the bare `up`, compare the existing container's creation time against the mtime of `.devcontainer/devcontainer.json` (and `.devcontainer/Dockerfile`, which is assembled and also only read at build).

Look the container up by the label the CLI sets, which is the workspace folder:

```bash
docker inspect "$(docker ps -aq --filter label=devcontainer.local_folder=<abs workspace path>)" \
  --format '{{.Created}}'
```

When the container is older than the config, do **not** silently reuse it. Options to weigh, with a recommendation recorded in the task notes:

- print a prominent warning naming both timestamps and the `rebuild=true` fix, and continue; or
- escalate to `--remove-existing-container` automatically (expensive, and surprising mid-run); or
- refuse to start and tell the operator to pass `rebuild=true`.

Prefer the least surprising option that cannot be missed — a warning buried in normal output is close to no warning, which is how this went unnoticed for three days.

Degrade cleanly when the information is unavailable: no `docker` on PATH, no matching container, or an `inspect` failure must not break the launch. The check is advisory.

## Out of scope

- Changing the default of `rebuild` (it stays off; a rebuild is expensive).
- The `.claude` overlay design itself (TASK-239) — this task only detects that it is not applied.
- `ralph upgrade`'s own file handling.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 start_devcontainer compares the existing container's creation time against the mtime of .devcontainer/devcontainer.json and .devcontainer/Dockerfile before reusing it
- [ ] #2 When the container is older than either file, the operator sees an unmissable message naming both timestamps and the rebuild=true remedy
- [ ] #3 The chosen behaviour on detection (warn, auto-recreate, or refuse) is implemented and its rationale recorded in the task notes
- [ ] #4 A missing docker binary, no matching container, or a failing docker inspect leaves the launch working exactly as it does today
- [ ] #5 A test covers the stale case, the current case, and each degraded case, with the container creation time and the file mtimes stubbed rather than requiring a real container
- [ ] #6 rebuild defaults to off and its behaviour is unchanged when passed explicitly
- [ ] #7 uv run ruff check . and uv run pytest both pass
<!-- AC:END -->
