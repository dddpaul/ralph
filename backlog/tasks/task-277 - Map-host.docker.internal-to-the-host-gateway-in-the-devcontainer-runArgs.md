---
id: TASK-277
title: Map host.docker.internal to the host gateway in the devcontainer runArgs
status: Done
assignee: []
created_date: '2026-10-17 15:52'
updated_date: '2026-10-18 09:11'
labels:
  - 'feature:ralph-init'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

The devcontainer template depends on `host.docker.internal` twice: `containerEnv` routes all HTTP(S) through the host Squid at `http://host.docker.internal:3128` (and `init-firewall.sh` fetches `https://api.github.com/meta` through it, exiting 1 when that fails), and `MCP_GATEWAY_HOST` is fixed to `host.docker.internal`. Docker Desktop and colima resolve that name to the host, but a plain Linux Docker Engine does not, so on a Linux host - such as the WSL2 Ubuntu 24.04 "agentbox" the mycloud project provisions to run Ralph - `devcontainer up` fails at `postStartCommand` (`waitFor: postStartCommand`) even when a proxy listens on the host. Image build and container creation are fine there; only the name is missing.

Measured from mycloud on 2026-10-17 (Docker 29.9.1, @devcontainers/cli 0.89.0): `--add-host=host.docker.internal:host-gateway` resolves to the host on every runtime that matters. On colima it gives 192.168.5.2 - the Mac, the same address colima's DNS already returns, so the Mac path is unchanged. On Docker Desktop `host-gateway` is the host by design. On a Linux engine it is the bridge gateway, i.e. the Linux host itself.

## Scope

In scope:
- Add `--add-host=host.docker.internal:host-gateway` to `runArgs` in the devcontainer template and in this repo's own `.devcontainer/devcontainer.json`, keeping `--cap-add=NET_ADMIN` and `--cap-add=NET_RAW`.
- A comment next to it saying why (Linux engines do not define the name; host-gateway is the host on Docker Desktop, colima and Linux).
- A pytest assertion in the existing devcontainer JSON test style pinning the runArg in both files.
- ralph-init docs: replace the "colima caveat" note with the runArg's effect, and state the remaining Linux-host prerequisite plainly: something must listen on 3128 on the host, reachable from the bridge (e.g. bound to the docker0 gateway address or 0.0.0.0), for the proxy path to work.

Out of scope:
- Making the Squid proxy optional or changing what traffic goes through it - the proxy is a deliberate part of the sandbox design.
- Providing a proxy on any host (mycloud tracks the agentbox side itself).
- Any `init-firewall.sh` rule change.

## Files

- `plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json` (exists) - add the runArg and its comment.
- `.devcontainer/devcontainer.json` (exists) - same change, for template parity (R11).
- `tests/python/devcontainer_config.py` (exists) - shared helper the devcontainer JSON tests use; a new or existing `tests/python/test_devcontainer_*.py` asserts the runArg.
- `plugins/ralph/skills/ralph-init/SKILL.md` (exists) - the "colima caveat" note under "Host MCP gateway slot" and the proxy prerequisite.

## Source

Source: /Users/paul/Private/Projects/mycloud@88093de285c8-dirty
Source context (read-only, do NOT modify): /Users/paul/Private/Projects/mycloud/backlog/tasks/task-52 - Docker-and-devcontainer-CLI-for-Ralph.md (implementation notes record the agentbox measurements)

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, build command, or visible behavior - not "works correctly").
3. All dependencies in the task's frontmatter are status=Done.
4. Out-of-scope items are not accidentally pulled in by ambiguous AC.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 runArgs in plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json contains --add-host=host.docker.internal:host-gateway alongside --cap-add=NET_ADMIN and --cap-add=NET_RAW (grep)
- [x] #2 .devcontainer/devcontainer.json carries the same runArgs entry, keeping template parity
- [x] #3 A pytest test pins the runArg in both files, and uv run pytest passes
- [ ] #4 devcontainer up --workspace-folder . on the developer's host succeeds with the new runArgs, postStartCommand's firewall verification passes, and the in-container output of getent hosts host.docker.internal is recorded in the task notes
- [x] #5 plugins/ralph/skills/ralph-init/SKILL.md no longer carries the colima caveat and states that a Linux host must serve the proxy on 3128 reachable from the docker bridge (grep)
- [x] #6 uv run ruff check . passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Handoff acceptance gate (autonomous): YELLOW. All four (exists) paths present; no dependencies; out-of-scope items (proxy optionality, host proxy, init-firewall.sh) are separable. One check fails: AC #4 needs devcontainer up on the developer's host, but this run executes inside the devcontainer with no docker/devcontainer CLI and no docker socket, so it cannot be performed here - it is recorded as PENDING HOST-SIDE VERIFICATION, not checked off blind (TASK-242 precedent). Source repo (/Users/paul/...mycloud) is not mounted; the task body specifies enough to reach every other AC.
Plan: add --add-host=host.docker.internal:host-gateway to runArgs in both devcontainer.json copies with a whole-line // comment explaining why; new tests/python/test_devcontainer_host_gateway.py pinning the runArg and the two caps in both copies plus the comment; rewrite the colima caveat in ralph-init SKILL.md to describe the runArg and the Linux-host 3128 prerequisite; README if it mentions the caveat.

Commit: `57a29b6` - task-277: map host.docker.internal to the host gateway in the devcontainer runArgs

PENDING HOST-SIDE VERIFICATION (AC #4) - not checked off blind. devcontainer up --workspace-folder . could not be run: this autonomous run executes inside the devcontainer, which has no docker CLI, no devcontainer CLI and no docker socket. Follow-up for the developer on the host: run devcontainer up --workspace-folder . (it must pass postStartCommand's init-firewall.sh verification), then devcontainer exec --workspace-folder . getent hosts host.docker.internal, and record that output here before ticking AC #4.
Done: runArgs in .devcontainer/devcontainer.json and the ralph-init template (still byte-identical) now read ["--cap-add=NET_ADMIN", "--cap-add=NET_RAW", "--add-host=host.docker.internal:host-gateway"]. The array stays on one line so merge-runargs.sh keeps merging it in Upgrade U4, and a whole-line comment above it says why. New tests/python/test_devcontainer_host_gateway.py runs on both copies and checks: the runArg is present exactly once, both caps are kept, the array is one line, the comment explains it, the proxy and MCP gateway vars still name host.docker.internal, and a mutation that drops the runArg is caught. In ralph-init SKILL.md the colima caveat is replaced by a note on what the runArg does on Docker Desktop, colima and Linux engines; the note says U4 carries the element into existing projects and states the Linux-host prerequisite: the Squid proxy on 3128 must be reachable from the docker bridge (docker0 gateway address or 0.0.0.0). uv run pytest: 913 passed, 3 skipped. uv run ruff check .: clean. task-reviewer: APPROVED, deferral of AC #4 accepted.

Commit: `f3e4384` - task-277: bump plugin version to 0.14.5 (patch)
<!-- SECTION:NOTES:END -->
