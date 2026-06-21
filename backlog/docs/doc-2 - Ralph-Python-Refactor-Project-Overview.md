---
id: doc-2
title: 'Ralph Python Refactor: Project Overview'
type: guide
created_date: '2026-06-21 13:07'
---

## Feature

`feature:ralph-python-refactor` — port the Ralph autonomous-loop orchestrator from bash to Python.

## Spec

Full PRD: `design/ralph-python-refactor-prd.md`. The PRD is the single source of truth for user stories, functional requirements, design considerations, and the 30-entry historical-context appendix. This doc is a navigation sheet, not a duplicate.

## Goal

Port `skills/ralph-run/scripts/ralph.sh` (~895 lines bash) and the three helpers (`preflight.sh`, `wait-heartbeat.sh`, `usage-check.sh`) to Python 3.14 + uv with PEP 723 inline metadata. Strict port — byte-identical status JSON, same CLI surface, same on-disk log format. New features deferred to post-cutover.

## Tech Stack

- **Language:** Python 3.14 (orchestrator); Bash (hooks, git hooks, sync, firewall — unchanged); Markdown (skills, agents, docs)
- **Runtime manager:** uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Python deps:** `pydantic>=2.5` only. Stdlib for everything else (subprocess, signal, argparse, pathlib, json, threading, queue)
- **Test:** pytest
- **Lint:** ruff (`uv run ruff check skills/ralph-run/scripts`)
- **Typecheck:** pyright --strict (`uv run pyright --strict skills/ralph-run/scripts`)
- **Distribution:** Source IS the artifact. PEP 723 inline metadata is the dependency lock. No `pyproject.toml [project]`, no `uv.lock`, no CI. Propagated via `/ralph-sync` like today's bash.

## Architecture

```
skills/ralph-run/scripts/
├── ralph_orchestrator.py         # entry point, PEP 723 inline metadata
├── ralph/                        # sibling package
│   ├── __init__.py
│   ├── status.py                 # pydantic StatusFile model
│   ├── signals.py                # sentinel parsing
│   ├── tasks.py                  # backlog CLI wrapper
│   ├── heartbeat.py              # daemon thread
│   ├── usage.py                  # usage-check wrapper
│   ├── preflight.py              # preflight port
│   ├── wait_heartbeat.py         # wait-heartbeat port
│   ├── usage_check.py            # usage-check port
│   └── tools/
│       ├── __init__.py           # Tool ABC
│       ├── claude.py
│       └── opencode.py
└── tests/
    ├── fixtures/fake_claude.py
    └── scripts/check_run_clean.py
```

Strangler-fig dispatch: outer `ralph.sh` shim reads `RALPH_IMPL=bash|python` env var; both implementations coexist during dual-running window (US-006), bash is deleted at cutover (US-007).

`pyproject.toml` at repo root is **tool-config only** (`[tool.ruff]`, `[tool.pyright]`). No `[project]` table — there is no package to publish.

## Scope

**In scope:**
- Port `ralph.sh` + 3 helpers to Python
- Byte-identical status JSON (golden round-trip test)
- Exact CLI parity (same flag names, same defaults, same exit codes)
- pyproject.toml tool config + pyright/ruff/pytest setup
- Strangler-fig `RALPH_IMPL` env dispatch + `/ralph-run impl=` arg
- ralph-init R11 template mirrors (outer ralph.sh + devcontainer Dockerfile.base only)

**Out of scope (deferred):**
- New CLI flags, new sentinels, new retry policy, schema changes
- Worktree isolation, external reviewer, notifications, --plan mode
- Hook changes (stay bash), git-hook changes, sync.sh, utc-to-moscow.sh, init-firewall.sh
- CI/PyPI publishing

## Task Dependency Graph

```
TASK-149 (US-000: ralph-sync directory spike — precondition)
    ↓
TASK-150 (US-001: scaffold + StatusFile pydantic contract)
    ↓
    ├── TASK-151 (US-002: helpers — parallelizable with 152)
    └── TASK-152 (US-003: core internals — parallelizable with 151)
                  ↓
                  TASK-153 (US-004: claude subprocess + process-group cleanup)
                      ↓
                      TASK-154 (US-005: opencode + entry point + E2E test)
                          ↓
                          TASK-155 (US-006: strangler integration + ralph-init mirror)
                              ↓
                              TASK-156 (US-007: cutover + cleanup + downstream upgrade)
```

## Cutover Gate

5 consecutive `RALPH_IMPL=python` runs each pass `tests/scripts/check_run_clean.py --run-only`. "Clean" means:
- `state=completed` AND `exit_code=0` AND `errors=[]`
- ≥1 task moved To Do → Done
- Heartbeat fresh throughout (sampled every 5s)
- No leftover child processes

After flipping default to Python, 5 more clean runs are required before deleting bash.

## R16 Reminder (for task implementers)

Per the PRD §10 reviewer cross-checks: port tasks reference `design/ralph-python-refactor-prd.md` and bash source line ranges as the spec. They do NOT reference historical task IDs (e.g., the bash TASK-NN that originally implemented a feature). The historical-invariants live verbatim in the PRD's §7 appendix — read them there.
