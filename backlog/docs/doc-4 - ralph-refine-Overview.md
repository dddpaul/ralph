---
export: true
id: doc-4
title: ralph-refine Overview
type: other
created_date: '2026-07-22 16:25'
---

# ralph-refine Overview

Reference sheet for the `ralph-refine` feature. Full design:
`design/ralph-refine-brainstorm.md` + `design/ralph-refine-prd.md`.

## Goal

Rewrite the standalone `refine` adversarial author-reviewer refinement loop
(`~/dev/ai/refine`, bash `refine.sh`) as a Python-based, separately-invocable
`ralph-refine` skill inside this repo (the Ralph plugin marketplace), reusing
the plugin's existing tool / devcontainer / signal layer. It is Ralph's
non-code sibling loop: Ralph loops a *coder* over backlog tasks; ralph-refine
loops an *author-reviewer* over a digital artifact (md / draw.io / PlantUML)
until a quality score threshold.

## Tech Stack

- Python 3.14 + uv (PEP-723 entrypoint), pydantic where useful
- Reuses the `ralph` package under
  `plugins/ralph/skills/ralph-run/scripts/` (single pinned Python root)
- Bash shim (`refine.sh`) + Claude Code plugin skill (`SKILL.md` + examples)
- Tooling bar: `uv run pytest`, `uv run ruff check .`, `pyright` strict

## Architecture

- **New sub-package** `ralph/refine/`: `args`, `roles`, `extract`, `loop`,
  `summary`, `cli`. Thin entrypoint `refine_orchestrator.py` mirrors
  `ralph_orchestrator.py`.
- **Reused verbatim:** `ralph.tools` (claude/opencode + `_subprocess.execute`:
  timeout=124, tee, process-group kill), `ralph.devcontainer`, `ralph.signals`.
- **Not reused:** `ralph.loop` (backlog/one-task-STOP coupled), `ralph.prompts`,
  `ralph.status`/`ralph.heartbeat` (phase-2 detach only).
- **Skill scope (Option A):** `skills/ralph-refine/` owns `SKILL.md` + `examples/`
  + shim; Python lives in the shared root.
- **Entrypoint:** repo-root `refine.sh` mirrors `ralph.sh`'s 5-tier resolver
  (-> `refine_orchestrator.py`); R11-paired template; seeded by `ralph-init`.

## Cross-Task Invariants (the reviewer must hold these across ALL tasks)

1. **Tool-layer reuse contract** - all LLM I/O flows through `ralph.tools`; the
   extractor reads `ToolResult.stdout_path` (combined stdout+stderr tee). No
   bespoke subprocess/timeout code.
2. **Tag protocol** - `<artifact>...</artifact>` (author), a line-anchored
   `^SCORE: N` (1-10) + `<summary>...</summary>` (reviewer) is the single
   contract shared by `roles.py`, `extract.py`, the example roles, and the e2e
   stub.
3. **R11 template parity** - repo-root `refine.sh` and
   `templates/root/refine.sh` stay byte-identical; the R11 table lists the pair.
4. **Single-approval launch** - when ralph-refine launches refine on the user's
   behalf, exactly ONE permission prompt fires (the sandbox-bypass `refine.sh`
   launch); helper shims are pre-authorized via seeded `Bash(bash <abs-path>:*)`
   allow rules - never a second prompt. Mirrors `ralph-run`.

## Scope

**In (phase 1, foreground CLI):** the `ralph/refine/` package, full `refine.sh`
CLI parity, author/reviewer/threshold loop, tag extraction, `refine.sh` shim +
R11 + init-seeding, 3 example role sets, `SKILL.md`, pytest/ruff/pyright green.

**Out (Non-Goals):** detached/watch execution (phase-2: `.refine-status.json`,
heartbeat, watch skill, launcher shim); common-package extraction; retiring
`~/dev/ai/refine` (separate follow-up in that repo); backlog integration;
separate-streams tool variant; new artifact types.

## Task Dependency Graph

```
TASK-201 (package scaffold + entrypoint)
   |-- TASK-202 (CLI args parse/validate)
   |-- TASK-203 (tag/score extraction)
   \-- TASK-204 (prompt composition)
          \-- TASK-205 (threshold loop)   [dep: 202,203,204]
                 |-- TASK-206 (refine.sh shim + R11 + init seed)
                 |-- TASK-207 (example roles)
                 \-- TASK-208 (SKILL.md + single-approval flow)
                        \-- TASK-209 (fake-claude e2e + green bar)  [dep: 205,206,207,208]
```
