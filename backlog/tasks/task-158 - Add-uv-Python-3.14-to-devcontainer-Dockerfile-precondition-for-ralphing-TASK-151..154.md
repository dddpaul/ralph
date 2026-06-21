---
id: TASK-158
title: >-
  Add uv + Python 3.14 to devcontainer Dockerfile (precondition for ralphing
  TASK-151..154)
status: In Progress
assignee: []
created_date: '2026-06-21 14:21'
updated_date: '2026-06-21 14:40'
labels:
  - 'feature:ralph-python-refactor'
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Devcontainer currently has Node 20 + Go 1.25 base, no Python toolchain. TASK-151..156 each carry `uv run pyright|ruff|pytest` ACs that need uv + Python 3.14 inside the container. These additions are AC #3, #5, #6 of TASK-155 but are independent of the strangler dispatch (which depends on the Python orchestrator existing). Pull them forward so the devcontainer can host Ralph autonomous runs of TASK-151..154.

After TASK-158 merges, TASK-155 narrows to: strangler RALPH_IMPL dispatch in outer shim + `impl=` skill arg + smoke tests.

Spec sources:
- `.devcontainer/Dockerfile` (live — needs uv + Python 3.14 install)
- `skills/ralph-init/templates/devcontainer/Dockerfile.base` (R11 template mirror — must match live)
- `skills/ralph-init/SKILL.md` (Prerequisites paragraph for host-mode uv install)
- TASK-155 ACs #3, #5, #6 (to be removed atomically and replaced with a single backref)

This is a MANUAL task (uses Docker build, not autonomously runnable from inside a non-Python devcontainer).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Live `.devcontainer/Dockerfile` adds `COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv` and `RUN uv python install 3.14` (unconditional — Ralph orchestrator requires it regardless of project language)
- [x] #2 R11 mirror: `skills/ralph-init/templates/devcontainer/Dockerfile.base` adds the same uv install lines with inline comment `# required by Ralph orchestrator regardless of project language`
- [x] #3 Container image rebuilt; inside the rebuilt container, `uv --version` succeeds and `uv run python -c 'import sys; print(sys.version)'` reports 3.14.x
- [x] #4 TASK-155 has ACs #3, #5, #6 removed (those AC lines no longer exist in the task file); a single backref AC is added pointing at TASK-158 as the precondition
- [x] #5 TASK-155 dependencies updated: `--dep TASK-158` added (TASK-155 still depends on TASK-154 too)
- [x] #6 `skills/ralph-init/SKILL.md` gains a Prerequisites paragraph that leads host-mode uv install with OS package managers (e.g. `brew install uv`, `pacman -S uv`, `dnf install uv`, `pipx install uv`) and cites `curl -LsSf https://astral.sh/uv/install.sh | sh` only as a last-resort fallback
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementation complete.

AC #1: .devcontainer/Dockerfile lines 97-102 added uv multi-stage COPY + RUN uv python install 3.14 between Claude install and Firewall sections.
AC #2: skills/ralph-init/templates/devcontainer/Dockerfile.base lines 85-90 mirror the same additions at the matching insertion point (same comment + same USER root/USER node switches).
AC #3: skills/ralph-init/SKILL.md gained a 'Prerequisites' section before Step 1; leads host install with brew/pacman/dnf/pipx and cites curl|bash as last-resort fallback per user feedback (see feedback_install_via_package_manager.md). PRD lines 126 + 367 updated with the same wording so the spec tracks current intent.
AC #4: devcontainer build succeeded (exit 0, image vsc-ralph-94baa4c13af3d41fdf2eace4aa4cde752579681a5888cb751761afe5c4c77e1f); docker run uv --version reports 0.11.23; 'uv run --python 3.14 python -c "import sys; print(sys.version_info[:2])"' reports (3, 14).
AC #5: TASK-155 ACs #3, #5, #6 removed (descending-order --remove-ac 6 5 3); new AC #8 backref added: 'Devcontainer uv + Python 3.14 toolchain is present (precondition from TASK-158)'. Description body rewritten to clarify the split + validator [llm] re-evaluation now OK.
AC #6: TASK-155 frontmatter dependencies now lists TASK-158 (added via --dep task-158).
<!-- SECTION:NOTES:END -->
