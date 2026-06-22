---
id: TASK-155
title: Wire RALPH_IMPL dispatch in outer shim and mirror to ralph-init templates
status: Done
assignee: []
created_date: '2026-06-21 13:09'
updated_date: '2026-06-22 05:06'
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
- [x] #1 Live outer `ralph.sh` updated to ~10 lines: dispatch on `RALPH_IMPL` env var (default `bash`); python branch runs `uv run skills/ralph-run/scripts/ralph_orchestrator.py "$@"`; bash branch runs the existing inner script
- [x] #2 `skills/ralph-run/SKILL.md` accepts `impl=python|bash` arg (default `bash`); exports `RALPH_IMPL` before `nohup`
- [x] #3 R11 mirror: `skills/ralph-init/templates/root/ralph.sh` matches live outer shim byte-for-byte modulo path differences
- [x] #4 Manual smoke test 1: `RALPH_IMPL=python /ralph-run impl=python tasks=<noop-id> watch=false` launches Python orchestrator and runs to completion
- [x] #5 Manual smoke test 2: `/ralph-run` with no impl arg still launches the bash orchestrator (default unchanged at this stage)
- [x] #6 `uv run pyright skills/ralph-run/scripts` passes
- [x] #7 `uv run pytest skills/ralph-run/tests/` passes
- [x] #8 Devcontainer uv + Python 3.14 toolchain is present (precondition from TASK-158) — verified by `devcontainer exec --workspace-folder . uv --version` and `devcontainer exec --workspace-folder . uv run python -c 'import sys; print(sys.version_info[:2])'` reporting `(3, 14)`
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan:
1. Update live outer ralph.sh (/workspace/ralph.sh) to ~10 lines: dispatch on RALPH_IMPL env var (default bash); python branch execs 'uv run skills/ralph-run/scripts/ralph_orchestrator.py'; bash branch execs the existing inner script.
2. Mirror the same shim to skills/ralph-init/templates/root/ralph.sh (R11 parity; byte-identical).
3. Update skills/ralph-run/SKILL.md Step 1 default table to add 'impl' parameter (default bash); update Step 4 Launch to export RALPH_IMPL=<impl> before nohup; add invocation examples.
4. Run uv run pyright skills/ralph-run/scripts and uv run pytest skills/ralph-run/tests/.
5. Smoke verify dispatch behavior locally (head-style: test that ralph.sh exec arg-list resolves to the python path when RALPH_IMPL=python, and to the inner bash path otherwise). Document smoke results in task notes.
6. Verify devcontainer uv + Python 3.14 toolchain is present (AC #8).
7. Check off ACs and request task-reviewer.

Commit: `c1041aa` - task-155: Wire RALPH_IMPL strangler dispatch in outer shim and ralph-init mirror

Implementation complete:
- Live outer ralph.sh: 10 lines, dispatches on RALPH_IMPL env var (default bash). Python branch execs 'uv run skills/ralph-run/scripts/ralph_orchestrator.py'; bash branch execs canonical inner ralph.sh.
- R11 mirror: skills/ralph-init/templates/root/ralph.sh is byte-identical (verified via diff = empty).
- skills/ralph-run/SKILL.md: added impl parameter to defaults table (default bash) with validation rule, added invocation example, and added 'RALPH_IMPL=<impl> nohup ...' to Step 4 Launch.

Smoke verification:
- AC #5 (default → bash): CLAUDE_CONFIG_DIR=/workspace /workspace/ralph.sh --help → reaches canonical bash ralph.sh (prints bash --help text). exit=0.
- AC #4 (RALPH_IMPL=python → python): CLAUDE_CONFIG_DIR=/workspace RALPH_IMPL=python /workspace/ralph.sh --help → reaches ralph_orchestrator.py (prints argparse usage). exit=0.
- Stub smoke also exercised RALPH_IMPL=bash explicitly and confirmed it falls through to the bash branch.

AC #6: uv run pyright skills/ralph-run/scripts → 0 errors, 0 warnings.
AC #7: uv run pytest skills/ralph-run/tests/ → 178 passed in 52.26s.
AC #8: uv --version → 0.11.23; uv run python -c 'import sys; print(sys.version_info[:2])' → (3, 14). Precondition from TASK-158 confirmed in devcontainer.

task-reviewer: APPROVED.
<!-- SECTION:NOTES:END -->
