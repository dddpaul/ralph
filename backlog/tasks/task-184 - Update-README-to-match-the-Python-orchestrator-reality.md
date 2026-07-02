---
id: TASK-184
title: Update README to match the Python-orchestrator reality
status: Done
assignee: []
created_date: '2026-07-01 20:10'
updated_date: '2026-07-02 06:41'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
README.md drifted from the codebase after the Python cutover (TASK-156), the model-default change (TASK-179), and the Mode Gate (TASK-181). Fix the confirmed factual inaccuracies against the actual code. Verified discrepancies: (1) intro L5 and Key Files table L227 call ralph.sh 'the bash loop' — it is a 7-line shim execing a Python orchestrator (skills/ralph-run/scripts/ralph/*.py) via uv; L312 'Shim and Canonical Orchestrator' already describes this correctly, so reconcile. (2) CLI Options --model default L146 says claude-opus-4-6; actual default is claude-opus-4-8 (args.py:81). (3) Mandatory Code Review L285 says 'spawns an Explore agent'; it spawns the task-reviewer agent (CLAUDE.md step 4). (4) Prerequisites L13-20 omit uv + Python 3.14, which the orchestrator requires. (5) Testing section L381-440 documents only bats/npm; the orchestrator has a pytest suite (skills/ralph-run/tests/test_*.py, run via uv run pytest) — document both and clarify the split (bash hooks = bats, Python orchestrator = pytest); verify what npm test actually runs now. (6) Dual Mode section L214-221 does not mention the interactive Implementation Mode Gate (ask Ralph vs interactive before implementing any task). Leave the Go 1.25 devcontainer note (template default) and flowchart/ (still present) as-is.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 README intro and Key Files table describe ralph.sh as a thin shim execing the Python orchestrator via uv (no 'bash loop' wording), consistent with the existing Shim and Canonical Orchestrator section
- [x] #2 CLI Options table shows --model default as claude-opus-4-8
- [x] #3 Mandatory Code Review section names the task-reviewer agent (not an Explore agent)
- [x] #4 Prerequisites list includes uv and Python 3.14 as requirements for the orchestrator
- [x] #5 Testing section documents the Python pytest suite (uv run pytest) alongside the bash bats tests, and accurately reflects what npm test currently runs
- [x] #6 Dual Mode section mentions the interactive Implementation Mode Gate (ask Ralph vs interactive before implementing a task)
- [x] #7 No other factual regressions introduced; Go 1.25 devcontainer note and flowchart/ references left intact
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Verified all 6 discrepancies against code. (1) ralph.sh=8-line shim execing uv run ralph_orchestrator.py -> reframe intro L5 + Key Files L227 as thin shim, no 'bash loop'. (2) args.py:81 default=claude-opus-4-8 -> fix L146. (3) CLAUDE.md step 4 spawns task-reviewer -> fix L285 (was Explore). (4) .python-version=3.14, pyproject target py314, Dockerfile installs uv+3.14 -> add uv+Python 3.14 to Prerequisites L13-20. (5) pytest suite skills/ralph-run/tests/test_*.py (24 files) via 'uv run pytest'; npm test=bats over tests/unit,integration,e2e -> document both suites + split (bash surface=bats, Python orchestrator=pytest); refresh stale bats file list to match current ls. (6) Add Implementation Mode Gate (Ralph vs Interactive) to Dual Mode L214-221. Leave Go 1.25 note + flowchart/ intact (AC#7).

Commit: `545d840` - task-184: Update README to match Python-orchestrator reality (shim not bash loop, --model default 4-8, task-reviewer agent, uv+Python 3.14 prereqs, pytest+bats split, Implementation Mode Gate)

Done: README updated to match Python-orchestrator reality. All 7 AC checked. task-reviewer APPROVED (git diff master..HEAD, README.md only) — verified shim wording, --model claude-opus-4-8, task-reviewer agent, uv+Python 3.14 prereqs, pytest+bats split with every referenced filename existing on disk, Implementation Mode Gate, and Go 1.25/flowchart intact. Gate green: ruff clean, 185 pytest pass. Worked around a repo hook bug: commit-prefix-guard.sh:18 sed extraction is line-based and only matches single-line -m messages, so multi-line commit messages get blocked — used a single-line subject.
<!-- SECTION:NOTES:END -->
