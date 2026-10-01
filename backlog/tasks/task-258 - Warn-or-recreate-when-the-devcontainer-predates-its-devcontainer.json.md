---
id: TASK-258
title: Warn or recreate when the devcontainer predates its devcontainer.json
status: Done
assignee: []
created_date: '2026-10-01 07:12'
updated_date: '2026-10-01 12:06'
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
- [x] #1 start_devcontainer compares the existing container's creation time against the mtime of .devcontainer/devcontainer.json and .devcontainer/Dockerfile before reusing it
- [x] #2 When the container is older than either file, the operator sees an unmissable message naming both timestamps and the rebuild=true remedy
- [x] #3 The chosen behaviour on detection (warn, auto-recreate, or refuse) is implemented and its rationale recorded in the task notes
- [x] #4 A missing docker binary, no matching container, or a failing docker inspect leaves the launch working exactly as it does today
- [x] #5 A test covers the stale case, the current case, and each degraded case, with the container creation time and the file mtimes stubbed rather than requiring a real container
- [x] #6 rebuild defaults to off and its behaviour is unchanged when passed explicitly
- [x] #7 uv run ruff check . and uv run pytest both pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: in start_devcontainer (rebuild=False only) probe docker ps -aq --filter label=devcontainer.local_folder=<abs ws> + docker inspect {{.Created}}; compare to mtimes of .devcontainer/devcontainer.json and Dockerfile; on stale, print a banner to stderr and return STALE_CONTAINER_EXIT without running up. Every probe failure -> None -> launch unchanged.

Decision (AC #3): REFUSE. /ralph-run launches detached and deletes backlog/.ralph-launch.log once the heartbeat is fresh, so a warn-and-continue banner would literally be deleted unread — the same silent drift as today. Refusing kills the process before the heartbeat, wait-heartbeat.sh FAILs, and the skill shows the launch-log tail containing the banner: unmissable. Auto-recreate rejected: expensive and surprising, and it would change rebuild's opt-in contract. Cost: an mtime bump without a content change (e.g. a checkout touching devcontainer.json) is a false positive; the remedy is one rebuild, accepted over silent drift. The banner also names the by-hand devcontainer up --remove-existing-container, because ralph-refine calls start_devcontainer with no rebuild flag of its own. rebuild=True skips the probe entirely, argv unchanged.

Commit: `8392908` - task-258: refuse to reuse a devcontainer older than its devcontainer.json or Dockerfile

Commit: `8544200` - task-258: shell-quote the workspace path in the stale-container remedy

Implemented: ralph/devcontainer.py container_created_at/stale_inputs/_report_stale; start_devcontainer refuses (STALE_CONTAINER_EXIT=1) when rebuild is off and the labelled container predates devcontainer.json/Dockerfile. Tests: tests/test_devcontainer_stale.py (stale x2, current, missing Dockerfile, rebuild skip, 7 degraded probes, nanosecond parse, end-to-end); existing devcontainer tests stub the probe via an autouse fixture. Docs: README --rebuild row, ralph-run SKILL.md. task-reviewer APPROVED; applied its shlex.quote nit. Gotcha: ruff format with target py314 rewrites except (A, B): to the paren-less PEP 758 form, which Python <3.14 rejects; use a tuple constant.

Commit: `ebc8e4b` - task-258: bump plugin version to 0.9.0 (minor)
<!-- SECTION:NOTES:END -->
