---
id: TASK-155
title: Wire RALPH_IMPL dispatch in outer shim and mirror to ralph-init templates
status: To Do
assignee: []
created_date: '2026-06-21 13:09'
labels:
  - 'feature:ralph-python-refactor'
dependencies:
  - TASK-154
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
US-006 from design/ralph-python-refactor-prd.md.

Update the outer `ralph.sh` shim with `RALPH_IMPL=bash|python` dispatch, the `/ralph-run` skill with an `impl=python|bash` parameter, the devcontainer Dockerfile with an unconditional uv + Python 3.14 install, and the corresponding ralph-init template mirrors (R11).

Spec sources:
- `ralph.sh` (outer shim — to be updated)
- `skills/ralph-run/SKILL.md` (skill — needs impl= parameter and propagation)
- `.devcontainer/Dockerfile` (live Dockerfile — adds uv + Python 3.14)
- `skills/ralph-init/templates/root/ralph.sh` (R11 template mirror — must match live shim)
- `skills/ralph-init/templates/devcontainer/Dockerfile.base` (R11 template mirror — must match live Dockerfile additions)
- `skills/ralph-init/SKILL.md` (Prerequisites note about host-mode uv install)

R11 scope: the canonical orchestrator (`skills/ralph-run/scripts/ralph.sh` and its Python successor) is explicitly NOT in the R11 mirror set per existing template parity rules. Only the OUTER `ralph.sh` shim and the devcontainer Dockerfile.base mirror.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Live outer `ralph.sh` updated to ~10 lines: dispatch on `RALPH_IMPL` env var (default `bash`); python branch runs `uv run skills/ralph-run/scripts/ralph_orchestrator.py "$@"`; bash branch runs the existing inner script
- [ ] #2 `skills/ralph-run/SKILL.md` accepts `impl=python|bash` arg (default `bash`); exports `RALPH_IMPL` before `nohup`
- [ ] #3 Live `.devcontainer/Dockerfile` adds `COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv` and `RUN uv python install 3.14` (UNCONDITIONAL — Ralph orchestrator requires it regardless of project language)
- [ ] #4 R11 mirror: `skills/ralph-init/templates/root/ralph.sh` matches live outer shim byte-for-byte modulo path differences
- [ ] #5 R11 mirror: `skills/ralph-init/templates/devcontainer/Dockerfile.base` adds the same uv install lines with inline comment `# required by Ralph orchestrator regardless of project language`
- [ ] #6 `skills/ralph-init/SKILL.md` gains a "Prerequisites" paragraph describing host-mode uv install: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [ ] #7 Manual smoke test 1: `RALPH_IMPL=python /ralph-run impl=python tasks=<noop-id> watch=false` launches Python orchestrator and runs to completion
- [ ] #8 Manual smoke test 2: `/ralph-run` with no impl arg still launches the bash orchestrator (default unchanged at this stage)
- [ ] #9 `uv run pyright --strict skills/ralph-run/scripts` passes
- [ ] #10 `uv run pytest skills/ralph-run/tests/` passes
<!-- AC:END -->
