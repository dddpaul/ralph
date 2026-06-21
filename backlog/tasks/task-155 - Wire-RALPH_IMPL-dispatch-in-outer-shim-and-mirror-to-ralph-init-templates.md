---
id: TASK-155
title: Wire RALPH_IMPL dispatch in outer shim and mirror to ralph-init templates
status: To Do
assignee: []
created_date: '2026-06-21 13:09'
updated_date: '2026-06-21 14:45'
labels:
  - 'feature:ralph-python-refactor'
dependencies:
  - TASK-154
  - TASK-158
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
US-006 from design/ralph-python-refactor-prd.md.

Wire the strangler-fig dispatch: update the outer `ralph.sh` shim to choose between bash and Python orchestrators based on `RALPH_IMPL`, add the matching `impl=python|bash` parameter to the `/ralph-run` skill, mirror the shim to the ralph-init R11 template, and verify with two smoke tests.

The devcontainer toolchain (uv + Python 3.14 install in `.devcontainer/Dockerfile` + `templates/devcontainer/Dockerfile.base` R11 mirror + `ralph-init/SKILL.md` Prerequisites paragraph) is NOT part of this task. Those pieces were pulled forward into TASK-158 (precondition) so that TASK-151..154 could run autonomously inside the devcontainer before US-006 landed. AC #8 here verifies the precondition is in place.

Spec sources:
- `ralph.sh` (outer shim — to be updated)
- `skills/ralph-run/SKILL.md` (skill — needs `impl=` parameter and propagation)
- `skills/ralph-init/templates/root/ralph.sh` (R11 template mirror — must match live shim)

R11 scope: the canonical orchestrator (`skills/ralph-run/scripts/ralph.sh` and its Python successor) is NOT in the R11 mirror set per existing template parity rules. Only the OUTER `ralph.sh` shim is mirrored in this task. The `Dockerfile.base` R11 mirror was done in TASK-158.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Live outer `ralph.sh` updated to ~10 lines: dispatch on `RALPH_IMPL` env var (default `bash`); python branch runs `uv run skills/ralph-run/scripts/ralph_orchestrator.py "$@"`; bash branch runs the existing inner script
- [ ] #2 `skills/ralph-run/SKILL.md` accepts `impl=python|bash` arg (default `bash`); exports `RALPH_IMPL` before `nohup`
- [ ] #3 R11 mirror: `skills/ralph-init/templates/root/ralph.sh` matches live outer shim byte-for-byte modulo path differences
- [ ] #4 Manual smoke test 1: `RALPH_IMPL=python /ralph-run impl=python tasks=<noop-id> watch=false` launches Python orchestrator and runs to completion
- [ ] #5 Manual smoke test 2: `/ralph-run` with no impl arg still launches the bash orchestrator (default unchanged at this stage)
- [ ] #6 `uv run pyright skills/ralph-run/scripts` passes
- [ ] #7 `uv run pytest skills/ralph-run/tests/` passes
- [ ] #8 Devcontainer uv + Python 3.14 toolchain is present (precondition from TASK-158) — verified by `devcontainer exec --workspace-folder . uv --version` and `devcontainer exec --workspace-folder . uv run python -c 'import sys; print(sys.version_info[:2])'` reporting `(3, 14)`
<!-- AC:END -->
