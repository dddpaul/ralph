---
export: true
title: 'PRD: Ralph Bash → Python 3.14 + uv Refactor'
type: design
---

# PRD: Ralph Bash → Python 3.14 + uv Refactor

**Feature label:** `feature:ralph-python-refactor`
**Source brainstorm:** distillation of decisions captured here; brainstorm history is human-design archive (NOT to be referenced from per-task descriptions per R16 spirit)
**Status:** Ready for `/ralph-backlog`

---

## 1. Introduction / Overview

The Ralph autonomous-loop orchestrator (`skills/ralph-run/scripts/ralph.sh`, ~895 lines of bash) and three helper scripts (`preflight.sh`, `wait-heartbeat.sh`, `usage-check.sh`, ~300 lines together) carry the project's most complex bash code. They orchestrate every autonomous Ralph iteration: pick a task, build the autonomous-mode prompt, spawn the AI tool (claude-code or opencode) with `tee` for streaming + capture, parse the output for the `<promise>COMPLETE</promise>` sentinel and `## Task Summary` blocks, write structured status JSON, manage a heartbeat thread for liveness, gate on the 5h Anthropic usage block, and emit a run summary on every exit path.

The bash implementation has accumulated four kinds of friction:

- **R5 GNU/BSD portability tax** on every shell change (sed `-i`, `date` flag differences, BSD `find -mmin` truncation, `stat -f`/`stat -c`, `readlink -f`).
- **Status JSON manipulated by grep + sed** — 18 fields, no schema validation, easy to drift between writers and readers.
- **Sentinel parsing is string scraping** — works today but brittle; can't distinguish "task done" from "iteration failed, will retry."
- **Single-axis retry policy** (`--on-error stop|continue|retry`) treats a 503 the same as a syntax error.

This refactor ports the orchestrator and three helpers to **Python 3.14 + uv with PEP 723 inline metadata**. Distribution is unchanged: source IS the artifact, propagated via `ralph-sync` to `~/.claude/skills/ralph-run/scripts/`, no build, no CI, no lock file. The cutover uses a **strangler-fig dispatch** behind `RALPH_IMPL=bash|python` so rollback is one env var.

The port is explicitly **strict** — byte-identical status JSON, same CLI surface, same on-disk log format. New features (richer sentinels, pattern-based retry classification, cross-model reviewer, worktree isolation, notifications, `--plan` mode) are deferred to post-port tasks. This isolates language-change risk from behavior-change risk.

---

## 2. Goals

- Eliminate ~1200 lines of orchestrator+helpers bash, replacing with Python 3.14 modules using stdlib + pydantic 2.5+
- Preserve **byte-identical** `backlog/.ralph-status.json` schema and on-disk `backlog/.ralph-run.log` format
- Preserve **exact** CLI flag set: `--tool`, `--model`, `--effort`, `--timeout`, `--on-error`, `--retry-count`, `--log-file`, `--prompt-file`, `--tasks`, `--block-end-buffer-min`, `--devcontainer`, positional `max_iterations`
- Preserve the `MODE: autonomous (Ralph loop iteration <i> of <max>)` prompt prefix verbatim — load-bearing for CLAUDE.md autonomous-mode contract
- Add real test coverage: pytest unit suite + one end-to-end test against a fake claude-code shim
- Add type checking via `pyright` as a pre-`task-reviewer` gate
- Reduce GNU/BSD portability tax for the orchestrator surface (R5 still applies to surviving bash: hooks, git hooks, `sync.sh`, `utc-to-moscow.sh`, `init-firewall.sh`)
- Make follow-on §6 improvements (richer sentinel taxonomy, retry classification, external reviewer) trivial to land

---

## 3. User Stories

### US-000: ralph-sync directory-handling spike (precondition)
**Description:** As the maintainer, I need to know whether `.claude/skills/ralph-sync/sync.sh` correctly propagates nested directories (e.g., `ralph/` package, `tests/`) under `skills/ralph-run/scripts/`, so that the Python orchestrator (a multi-file package) can be distributed via the same `/ralph-sync` flow as today's bash files.

**Acceptance Criteria:**
- [ ] Throwaway test: create `skills/ralph-run/scripts/spike/dummy.txt`, run `/ralph-sync classify`, verify `[new] skill ralph-run` is reported (or directory contents specifically)
- [ ] Run `/ralph-sync apply`, verify `~/.claude/skills/ralph-run/scripts/spike/dummy.txt` appears
- [ ] If sync drops directories or files within them: fix `.claude/skills/ralph-sync/sync.sh` to recurse correctly
- [ ] If fix is needed, add a regression test (manual or automated) demonstrating directory propagation
- [ ] Clean up the throwaway `spike/` directory before marking Done
- [ ] Append-notes the verdict (worked-as-is OR fix-applied) so US-001 can proceed unblocked

### US-001: Scaffold + StatusFile pydantic contract
**Description:** As the Python implementer, I need a foundational scaffold (PEP 723 entry point, sibling `ralph/` package, tests directory, pyright/ruff config) plus a pydantic `StatusFile` model that produces byte-identical JSON output to today's bash writer, so that subsequent tasks can extend the package without reinventing the contract enforcement layer.

**Acceptance Criteria:**
- [ ] `skills/ralph-run/scripts/ralph_orchestrator.py` created with PEP 723 inline metadata: `requires-python = ">=3.14"`, `dependencies = ["pydantic>=2.5"]`
- [ ] `skills/ralph-run/scripts/ralph/__init__.py` and `skills/ralph-run/scripts/ralph/status.py` created
- [ ] `StatusFile` pydantic model defines all 18 fields with exact names matching today's bash schema: `pid`, `started_at`, `state`, `iteration`, `max_iterations`, `tool`, `tasks_done[]`, `tasks_remaining`, `current_task`, `last_iteration_duration`, `elapsed`, `errors[]`, `completed_at`, `exit_code`, `iteration_started_at`, `timeout_sec`, `paused_reason`, `paused_buffer_min`, `paused_remaining_min`, `paused_block_end_time`, `paused_at`
- [ ] `StatusFile.write_atomic(path)` writes via `tempfile.NamedTemporaryFile` + `os.replace()` — atomic from external readers' perspective
- [ ] Golden-file round-trip test in `tests/test_status.py`: load a sample bash-written `backlog/.ralph-status.json`, parse via pydantic, re-serialize, assert byte-equal to original (modulo unset-field handling — document and lock the rule)
- [ ] `pyproject.toml` at repo root with `[tool.ruff]` (line-length=88, target-version="py314", src=["skills/ralph-run/scripts"]) and `[tool.pyright]` (include + strict on the same path, `pythonVersion = "3.14"`)
- [ ] `uv run pyright skills/ralph-run/scripts` passes
- [ ] `uv run ruff check skills/ralph-run/scripts` passes
- [ ] Spike verification: `import ralph` resolves from `ralph_orchestrator.py` (PEP 723 + sibling-package contract works)

### US-002: Port helpers (preflight, wait_heartbeat, usage_check)
**Description:** As the Python implementer, I need the three bash helpers ported to Python with their exact exit-code contracts preserved, so that the orchestrator can call them via subprocess (during the strangler period) or import them (post-cutover) without changing semantics.

**Acceptance Criteria:**
- [ ] `ralph/preflight.py` ports `preflight.sh`: 5 ordered checks (To Do exists, Ralph-not-running via status+heartbeat-within-15s, devcontainer CLI if requested, ralph.sh executable, syntax check), output is exactly ONE line (`OK RALPH_PATH=<path>` or `ERROR: <reason>`), runs against invoker's PWD (never `cd`), uses `$TMPDIR` not `/tmp`, anchors backlog error parsing on the canonical error line (not substring grep for "not found")
- [ ] `ralph/wait_heartbeat.py` ports `wait-heartbeat.sh`: 10×1s poll window with 15s freshness criterion
- [ ] `ralph/usage_check.py` ports `usage-check.sh`: exit-code contract preserved — 0=ok, 1=pause (prints `block_end_in_<rem>min_below_<buffer>min_buffer` to stdout), 2=cannot-measure (sentinel flag file `backlog/.ralph-usage-check-disabled` to fire warning once)
- [ ] For each helper, pytest unit test covers: success path, failure path, edge cases (e.g., heartbeat file missing, ccusage missing, backlog empty)
- [ ] Parity test: feed identical inputs to bash helper and Python helper; assert identical stdout AND identical exit code for 5+ scenarios per helper
- [ ] Bash helpers (`preflight.sh`, etc.) stay in place — Python helpers unused by orchestrator until US-006
- [ ] `pyright` passes on all new files

### US-003: Port core internals (signals, tasks, heartbeat, usage, tool protocol)
**Description:** As the Python implementer, I need the orchestrator's internal building blocks ported: sentinel parsing, backlog CLI wrapper, heartbeat daemon thread, usage-cap wrapper, and the abstract Tool protocol that both claude and opencode will implement, so that US-004 and US-005 can drop in concrete executors without reinventing the surrounding plumbing.

**Acceptance Criteria:**
- [ ] `ralph/signals.py`: parses `<promise>COMPLETE</promise>` AND `^## Task Summary$` anchored regex (count must be ≤1 except when COMPLETE present); returns structured `IterationSignals` dataclass with `task_summary_count`, `complete`, `error_text` fields
- [ ] `ralph/tasks.py`: `pick_next_task()` queries `backlog task list -s "To Do" --plain`, returns lowest-ID task whose deps are all Done; supports `--tasks <ids>` whitelist that REPLACES the lowest-ID rule (whitelist-order iteration)
- [ ] `ralph/heartbeat.py`: starts a daemon `threading.Thread` that touches `backlog/.ralph-heartbeat` every 5s; exposes a `stop()` method that sets a `threading.Event` and `join(timeout=10)`s the thread; main process EXIT handler calls `stop()` and removes the heartbeat file
- [ ] `ralph/usage.py`: wraps `usage_check.py`, populates 5 `paused_*` fields on the StatusFile when pause is triggered, exposes `pause_state` named tuple for the orchestrator to write
- [ ] `ralph/tools/__init__.py`: defines `Tool` ABC with `run(prompt: str, timeout_sec: int) -> ToolResult` signature; `ToolResult` carries `exit_code`, `output_text` (the captured stdout), `duration_sec`
- [ ] Unit tests for each module; golden-file tests for signal parsing using captured sample outputs from real claude-code runs (committed under `tests/fixtures/`)
- [ ] `pyright` passes

### US-004: Port claude-code subprocess management
**Description:** As the Python implementer, I need `tools/claude.py` to spawn the claude-code child process with the same I/O semantics as today's bash (`claude --print 2>&1 | tee <outfile>`), enforce per-iteration timeout (exit 124 = timeout, NOT a `--on-error` failure), and clean up the entire child process tree on signal, so that the orchestrator preserves the load-bearing streaming + capture + cleanup contract.

**Acceptance Criteria:**
- [ ] `ralph/tools/claude.py` implements `Tool.run()`: spawns `claude --print` with stdin=prompt (heredoc-equivalent), stdout=PIPE, stderr=STDOUT (so `2>&1` semantics preserved); reads stdout line-by-line via a queue and writes to BOTH the temp file AND a real-time sentinel scanner
- [ ] Subprocess launched with `os.setpgrp` (or `start_new_session=True`) so the child gets its own process group
- [ ] Per-iteration `timeout_sec` enforced via `subprocess.Popen.wait(timeout=...)`; on timeout, send SIGTERM to the process group (`os.killpg`), wait 5s, then SIGKILL — orchestrator emits an "iteration timed out" warning, sleeps 2s, and CONTINUES (does NOT count as `--on-error` failure)
- [ ] SIGTERM handler in the orchestrator: kills the process group of the claude-code child but preserves the RUN_LOG tee equivalent so the final log line flushes before exit; final status JSON write sets `state=failed`, `exit_code=130` (or similar), no separate `interrupted` state
- [ ] Devcontainer prefix support: when `--devcontainer` is passed, the argv list is `["devcontainer", "exec", "--workspace-folder", <path>, "claude", "--print"]` — assembled as a LIST, never joined to a string (TASK-37 invariant)
- [ ] Unit test: spawn a sleeper child (`time.sleep(60)`) via `tools/claude.py`, send SIGTERM to the orchestrator process, assert child is gone within 5s (no zombie)
- [ ] Unit test: spawn a child that exits 124, assert orchestrator treats it as timeout (not `--on-error` failure)
- [ ] `pyright` passes

### US-005: Port opencode + wire entry point
**Description:** As the Python implementer, I need `tools/opencode.py` to mirror the claude-code subprocess pattern for the opencode CLI, plus the full orchestrator entry point (argparse → preflight → main loop → final status write) wired together, so that the Python implementation can run end-to-end against a fake claude-code shim.

**Acceptance Criteria:**
- [ ] `ralph/tools/opencode.py` implements `Tool.run()` for opencode using the same Popen + tee + sentinel scan + process-group cleanup pattern
- [ ] `ralph_orchestrator.py` entry point: `argparse.ArgumentParser.parse_intermixed_args()` accepting EXACT bash flag names — `--tool`, `--model`, `--effort`, `--timeout`, `--on-error`, `--retry-count`, `--log-file`, `--prompt-file`, `--tasks`, `--block-end-buffer-min`, `--devcontainer`, plus positional `max_iterations` (nargs="?")
- [ ] No auto short-flag inference (no `-t` for `--tool`); test exercises 5+ different flag/positional orderings to confirm `parse_intermixed_args` behaves
- [ ] Path resolution honors `RALPH_PROJECT_ROOT` env var (set by the outer shim); fallback to `pathlib.Path(__file__).parent` for standalone invocation
- [ ] Main loop: per-iteration → `usage.check_or_pause()` → `tasks.pick_next_task()` → build `MODE: autonomous (Ralph loop iteration <i> of <max>)` prefix → invoke tool → parse signals → diff `DONE_BEFORE`/`DONE_AFTER` via `tasks.list_done()` → update status → sleep 2s
- [ ] `--prompt-file` REPLACES the hardcoded inner prompt body; `MODE:` prefix STILL prepended; missing/unreadable file is hard fail with exit 1 before loop starts
- [ ] Run summary printed on every exit path: clean completion, max-iterations reached, `--on-error stop` abort, SIGINT/SIGTERM; closed set of exit reasons `{"all tasks done", "max iterations reached", "error", "interrupted"}`
- [ ] E2E test in `tests/test_e2e_fake_claude.py`: orchestrator runs end-to-end against `tests/fixtures/fake_claude.py` (mode=success), asserts status JSON has `state=completed`, `exit_code=0`, `errors=[]`, `tasks_done` contains the task the fake marked Done
- [ ] `pyright` passes

### US-006: Strangler integration + ralph-init mirror
**Description:** As the maintainer, I need the outer `ralph.sh` shim updated with `RALPH_IMPL` dispatch, the `/ralph-run` skill exposing an `impl=python|bash` parameter, the devcontainer Dockerfile installing uv + Python 3.14 unconditionally, and the corresponding ralph-init template mirrors, so that the dual-running window can begin and both implementations are available side-by-side.

**Acceptance Criteria:**
- [ ] Live outer `ralph.sh` (at repo root) updated to ~10 lines: `if [[ "${RALPH_IMPL:-bash}" == "python" ]]; then exec uv run "$CANONICAL_DIR/ralph_orchestrator.py" "$@"; fi; <existing exec to inner ralph.sh>`
- [ ] `skills/ralph-run/SKILL.md` accepts `impl=python|bash` parameter (default `bash`); exports `RALPH_IMPL=<value>` in the launch env before nohup
- [ ] Live `.devcontainer/Dockerfile` updated: adds `COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv` and `RUN uv python install 3.14` (UNCONDITIONAL — not language-gated)
- [ ] R11 mirror: `skills/ralph-init/templates/root/ralph.sh` matches the live outer shim byte-for-byte (modulo path differences)
- [ ] R11 mirror: `skills/ralph-init/templates/devcontainer/Dockerfile.base` adds the same uv + Python 3.14 install (UNCONDITIONAL); include an inline comment explaining "required by Ralph orchestrator regardless of project language"
- [ ] `skills/ralph-init/SKILL.md` gains a "Prerequisites" paragraph: host-mode bootstraps (`devcontainer=false`) require uv installed via the user's OS package manager (e.g. `brew install uv`, `pacman -S uv`, `dnf install uv`, `pipx install uv`) with `curl -LsSf https://astral.sh/uv/install.sh | sh` as a last-resort fallback
- [ ] Verify `ralph-sync` still works end-to-end with the new shim + new Dockerfile (depends on US-000 outcome)
- [ ] Manual smoke: `RALPH_IMPL=python /ralph-run impl=python tasks=<noop-id> watch=false` launches the Python orchestrator and runs to completion against a real backlog task in the devcontainer
- [ ] Manual smoke: `/ralph-run` (no `impl` arg) still launches the bash orchestrator (default unchanged)

### US-007: Cutover + cleanup + downstream upgrade
**Description:** As the maintainer, I need 5 consecutive clean Python runs verified via the mechanical check script, the default flipped to Python in both the live shim and the ralph-init template, 5 more clean runs as a burn-in window, then the inner bash orchestrator + helpers deleted and downstream-project upgrade instructions communicated, so that the refactor reaches steady-state.

**Acceptance Criteria:**
- [ ] `tests/scripts/check_run_clean.py --run-only` exists, codifies the 6-check clean-run gate (`state=completed`, `exit_code=0`, empty `errors[]`, ≥1 task moved To Do→Done during the run, heartbeat fresh throughout sampled every 5s, no leftover `claude-code`/`python`/`uv` processes after exit)
- [ ] `tests/scripts/check_run_clean.py --parity bash_status.json python_status.json` exists, checks schema parity (key set, key order; values may differ for timestamps/pids)
- [ ] 5 consecutive `RALPH_IMPL=python` runs each pass `--run-only`. Operator-driven; documented in the task notes with run dates and the resulting status JSON snapshots
- [ ] Default flipped to `python` in: live outer `ralph.sh`, `skills/ralph-run/SKILL.md` (skill default), `skills/ralph-init/templates/root/ralph.sh` (R11 mirror)
- [ ] 5 MORE consecutive clean runs with `RALPH_IMPL=python` as default (rollback to `bash` is still possible via env var) — bash burn-in window
- [ ] Inner bash orchestrator + helpers deleted: `skills/ralph-run/scripts/ralph.sh`, `skills/ralph-run/scripts/preflight.sh`, `skills/ralph-run/scripts/wait-heartbeat.sh`, `skills/ralph-run/scripts/usage-check.sh`
- [ ] Outer shim simplifies back to 6 lines pointing only at Python (both live and template)
- [ ] `/ralph-run` skill `impl=` parameter removed (no longer needed)
- [ ] `CLAUDE.md` Project-Specific section updated to note the bash orchestrator is gone; Language line tightened to "Python (orchestrator) + Bash (hooks, git hooks, sync, firewall) + Markdown (skills, agents, docs)"
- [ ] Downstream upgrade communication: task notes include explicit instructions — existing Ralph projects must run `ralph-init upgrade` to re-apply the new shim + Dockerfile.base, OR hand-patch those two files. This is the operator's call to action

---

## 4. Functional Requirements

- **FR-1:** The Python orchestrator MUST produce `backlog/.ralph-status.json` with byte-identical schema to today's bash writer: same 18 field names, same key order, same null handling, UTC `Z`-suffixed timestamps, no extra fields.
- **FR-2:** The Python orchestrator MUST accept the exact bash CLI flag set: `--tool`, `--model`, `--effort`, `--timeout`, `--on-error`, `--retry-count`, `--log-file`, `--prompt-file`, `--tasks`, `--block-end-buffer-min`, `--devcontainer`, positional `max_iterations`. No auto short-flag inference. No new flags.
- **FR-3:** Status JSON writes MUST be atomic from external readers' perspective (`tempfile.NamedTemporaryFile` in same dir + `os.replace()`).
- **FR-4:** Heartbeat MUST touch `backlog/.ralph-heartbeat` every 5s while orchestrator is running; orchestrator EXIT MUST clean up the heartbeat thread and remove the heartbeat file. Liveness criterion (consumer-side) remains `(now - mtime) < 15s`.
- **FR-5:** Per-iteration timeout MUST be enforced; exit code 124 (timeout) MUST trigger continuation (NOT counted as `--on-error` failure).
- **FR-6:** SIGTERM/SIGINT handlers MUST kill the entire child process group (not just the immediate child); the run summary MUST print before final exit.
- **FR-7:** Run summary MUST be printed on every exit path; exit reasons are the closed set `{"all tasks done", "max iterations reached", "error", "interrupted"}`.
- **FR-8:** `MODE: autonomous (Ralph loop iteration <i> of <max>)` prefix MUST be prepended to every iteration prompt verbatim — including when `--prompt-file` overrides the prompt body.
- **FR-9:** `<promise>COMPLETE</promise>` and `^## Task Summary$` (anchored regex) sentinel parsing MUST match today's bash behavior exactly.
- **FR-10:** The strangler-fig dispatch MUST honor `RALPH_IMPL=bash|python` env var; default is `bash` until cutover (US-007), then `python`.
- **FR-11:** The orchestrator MUST work both in-devcontainer (via `--devcontainer`) and on the host; devcontainer wrapping argv MUST be a list, never a joined string.
- **FR-12:** `RALPH_PROJECT_ROOT` env var MUST be honored for all project-relative path resolution; fallback to `Path(__file__).parent` for standalone invocation.
- **FR-13:** Usage-cap pause MUST honor exit-code contract from `usage_check.py`: 0=ok, 1=pause (with `block_end_in_<rem>min_below_<buffer>min_buffer` stdout), 2=cannot-measure (with sentinel flag file `backlog/.ralph-usage-check-disabled` to fire warning once); pause writes 5 `paused_*` fields + sets `state=paused`.
- **FR-14:** `--tasks` whitelist MUST replace the lowest-ID rule with whitelist-order iteration; each iteration MUST re-query backlog status (deps/states change); `tasks_remaining` counts whitelisted To Do IDs only; mutually exclusive with `--prompt-file`.
- **FR-15:** All Python code MUST pass `uv run pyright skills/ralph-run/scripts` and `uv run ruff check skills/ralph-run/scripts` before merge.
- **FR-16:** ralph-init templates `templates/root/ralph.sh` and `templates/devcontainer/Dockerfile.base` MUST be R11-mirrored from the live files in the same task that changes the live files.

---

## 5. Non-Goals (Out of Scope)

Explicit scope cuts. These are NOT in this refactor; they are deferred to post-port follow-on tasks.

- **No schema changes** to `backlog/.ralph-status.json`. Same 18 fields, same key order, same null handling.
- **No new CLI flags.** No flag renames. No new short flags.
- **No new sentinels.** `<promise>COMPLETE</promise>` and `## Task Summary` parsing unchanged. (Richer sentinel taxonomy is §6.1 — separate task post-cutover.)
- **No new retry policy.** `--on-error stop|continue|retry` semantics preserved. (Pattern-based retry classification is §6.4 — separate task post-cutover.)
- **No worktree isolation** per task. (§6.3 — separate task.)
- **No external (cross-model) reviewer.** (§6.2 — separate task.)
- **No notifications** (Telegram/webhook). (§6.6 — separate task.)
- **No `--plan` interactive mode.** (§6.5 — separate task.)
- **No hook changes.** All `.claude/hooks/*.sh` stay bash. R5 (GNU/BSD) still applies to surviving bash.
- **No git-hook changes.** `templates/git-hooks/*` stay bash.
- **No changes to** `sync.sh` (called from skill markdown), `utc-to-moscow.sh` (5-line awk one-liner), `init-firewall.sh` (iptables/ipset belongs in bash).
- **No `pyproject.toml` package declaration.** Tool-config only; no `[project]` section. PEP 723 inline metadata is the dependency declaration.
- **No CI pipeline.** Tests run via `uv run pytest` locally. No GitHub Actions for this refactor.
- **No `uv.lock` file.** PEP 723 inline metadata is the lock equivalent.
- **No structured `logging` migration.** Strict port uses `print()` for messages matching today's bash stdout; `logging.debug()` only for new Python-internal diagnostics. Migration to structured logging is a separate post-cutover concern.
- **No Python version upgrades** during the strict port. Pin `requires-python = ">=3.14"` and stay there.

---

## 6. Design Considerations

### Package Layout

```
skills/ralph-run/scripts/
├── ralph.sh                      # unchanged during port; deleted in US-007
├── preflight.sh                  # unchanged during port; deleted in US-007
├── wait-heartbeat.sh             # unchanged during port; deleted in US-007
├── usage-check.sh                # unchanged during port; deleted in US-007
├── ralph_orchestrator.py         # entry point, PEP 723 inline metadata (US-001)
├── ralph/                        # sibling package, found via sys.path[0]
│   ├── __init__.py
│   ├── status.py                 # StatusFile pydantic model (US-001)
│   ├── heartbeat.py              # daemon thread (US-003)
│   ├── signals.py                # sentinel parsing (US-003)
│   ├── tasks.py                  # backlog CLI wrapper (US-003)
│   ├── usage.py                  # ccusage wrapper (US-003)
│   ├── preflight.py              # ports preflight.sh (US-002)
│   ├── wait_heartbeat.py         # ports wait-heartbeat.sh (US-002)
│   ├── usage_check.py            # ports usage-check.sh (US-002)
│   └── tools/
│       ├── __init__.py           # Tool ABC (US-003)
│       ├── claude.py             # claude-code Popen + tee + signal parse (US-004)
│       └── opencode.py           # opencode Popen + tee + signal parse (US-005)
└── tests/
    ├── conftest.py               # pytest fixtures (tmpdir, fake-claude path)
    ├── fixtures/
    │   └── fake_claude.py        # canned shim (US-001 or US-005)
    ├── scripts/
    │   └── check_run_clean.py    # the cutover-gate check (US-007)
    ├── test_status.py
    ├── test_signals.py
    ├── test_preflight.py
    ├── test_usage_check.py
    ├── test_tasks.py
    ├── test_heartbeat.py
    ├── test_tools_claude.py
    └── test_e2e_fake_claude.py
```

### PEP 723 Inline Metadata (`ralph_orchestrator.py` header)

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["pydantic>=2.5"]
# ///
"""Ralph autonomous-loop orchestrator (Python port).

See design/ralph-python-refactor-prd.md for the full contract.
"""
```

### Strangler-Fig Dispatch (outer `ralph.sh` shim)

```bash
#!/usr/bin/env bash
# Thin shim — dispatches to bash or Python orchestrator based on RALPH_IMPL.
CANONICAL_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts"
if [[ "${RALPH_IMPL:-bash}" == "python" ]]; then
  exec uv run "$CANONICAL_DIR/ralph_orchestrator.py" "$@"
fi
RALPH_PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)" \
  exec "$CANONICAL_DIR/ralph.sh" "$@"
```

### `pyproject.toml` at Repo Root (tool config only, no package)

```toml
[tool.ruff]
line-length = 88
target-version = "py314"
src = ["skills/ralph-run/scripts"]

[tool.ruff.lint]
extend-select = ["I", "B", "UP", "SIM"]

[tool.pyright]
include = ["skills/ralph-run/scripts"]
strict = ["skills/ralph-run/scripts"]
pythonVersion = "3.14"
```

### Fake claude-code Shim Modes

`tests/fixtures/fake_claude.py` is a drop-in `claude-code` replacement. Invocation identical to real `claude-code` (ignores `--model`, `--effort`, `--print`; reads prompt from stdin). Extracts task ID from the prompt. Behavior via `FAKE_CLAUDE_MODE` env var:

- `success` (default): emits canned "doing things" → calls `backlog task edit <id> -s Done` → emits `## Task Summary` → emits `<promise>COMPLETE</promise>` → exits 0
- `task_done_no_summary`: same as success but skips Summary block (tests heuristic robustness)
- `fail`: emits error to stderr, exits 1
- `hang`: sleeps forever (tests timeout handling)

---

## 7. Technical Considerations

### Strict-port discipline

This refactor is **strict port, not feature port**. Acceptance criteria are framed around byte-identity (status JSON), behavior parity (CLI surface, signal handling), and zero behavior delta (no new sentinels, no new retry policy, no schema changes). When a port task hits ambiguity, the implementer consults the bash source line range named in the task — NOT historical task IDs in the task body — per R16 spirit.

### Historical context (load-bearing invariants)

The following appendix lists historical backlog tasks that document **load-bearing invariants** — behaviors that would be easy to "simplify away" during the port if the Python implementer didn't know WHY they exist. **Per-task READING is on-demand**, NOT primary input. Individual port tasks MUST NOT enumerate these task IDs in their description (R16 spirit). The PRD copies this list verbatim so that an implementer who hits ambiguity has the lookup available without leaving the spec.

#### Status JSON schema

- **TASK-6:** foundational `.ralph-status.json` contract — fields `pid, started_at, state (running/completed/failed), iteration, max_iterations, tool, tasks_done, tasks_remaining, current_task, last_iteration_duration, elapsed, errors[], completed_at, exit_code`; `tasks_done` is the diff of Done IDs before/after each iteration (the DONE_BEFORE/DONE_AFTER channel); written at every lifecycle point. Read if porting `status.py`.
- **TASK-13:** `current_task` is derived from the `To Do` query output (`grep -o 'TASK-[0-9]*' | head -1`) at iteration *start*, not from `In Progress` — the agent hasn't moved the task yet. Read if porting `status.py` / task picker.
- **TASK-24:** `current_task` must be re-queried from `In Progress` at iteration *end* — otherwise it's stale immediately. Two distinct writes per iteration, on purpose. Read if porting `status.py`.
- **TASK-14:** status/log file paths must be overridable via `RALPH_STATUS_FILE` / `RALPH_RUN_LOG` env vars so tests don't clobber real state. Read if porting `status.py`.
- **TASK-70:** status schema additions `iteration_started_at` (ISO, written at iter top) and `errors[]` as `{iteration, at, message}` objects (NOT bare strings) exist specifically so `ralph-status-watch` can detect stuck/failed-iter events stateless-ly. Read if porting `status.py` and `watch.py`. **(See also: Watch chain section below for the consumer-side detection rules.)**
- **TASK-42:** `elapsed` in the file is stale by design (only written at iteration boundaries) — readers compute live `elapsed = now - started_at` when `state=running`. Read if porting `status.py` consumers.
- **TASK-75:** all timestamps in JSON stay UTC with `Z` suffix; timezone conversion happens only in display skills. Do not change the on-disk format. Read if porting `status.py`.

#### Heartbeat

- **TASK-50:** heartbeat is a backgrounded subshell that `touch`es `backlog/.ralph-heartbeat` every 5s and self-terminates via `kill -0 $parent` polling — this is the SIGKILL-survivable liveness signal. EXIT trap must kill the HB child and remove the file. Read if porting `heartbeat.py` and process cleanup.
- **TASK-53:** freshness check uses `stat -f %m` (BSD) / `stat -c %Y` (GNU) + arithmetic, NOT `find -mmin -0.25` (BSD `find` truncates fractional minutes; silently always-false). The 15s threshold is 3× the 5s touch interval. Read if porting `heartbeat.py`.
- **TASK-77:** `wait-heartbeat.sh` is a separate script (not inline) with a fixed 10×1s poll window and 15s freshness criterion for first-detection after launch; exists as a script to fit narrow bash-allowlist permissions. Read if porting `wait_heartbeat.py`.
- **TASK-43:** double-run guard reads `pid` from the status JSON and uses `kill -0` — this is the explicit anti-double-start contract, moved from the skill into `ralph.sh` so it's enforced regardless of invoker. Read if porting `ralph.py` startup.

#### Sentinel parsing

- **TASK-18:** per-iteration check counts `^## Task Summary$` blocks in the captured output (anchored regex to avoid matching quoted CLAUDE.md text). Expected count = 1, except when `<promise>COMPLETE</promise>` is present (legitimate 0-block case). Warning-only, not fatal — observability of the one-task-per-iteration invariant. Read if porting `iteration.py`.
- **TASK-1:** agent invocation must be `timeout ... claude <<< $PROMPT | tee` (heredoc/process-sub, NOT `echo $PROMPT | timeout ... | tee`) so `PIPESTATUS[0]` captures the AI tool's exit code, not `echo`'s. Read if porting subprocess invocation.

#### Usage-cap pause

- **TASK-135:** `usage-check.sh` contract is exit-code-based — 0=ok, 1=pause (prints `block_end_in_<rem>min_below_<buffer>min_buffer`), 2=cannot measure. The 5 `paused_*` JSON fields (`paused_reason`, `paused_buffer_min`, `paused_remaining_min`, `paused_block_end_time`, `paused_at`) all exist for a reason: `paused_remaining_min` is what the check saw at trip time, `paused_block_end_time` is the absolute ccusage timestamp for resume planning — neither is redundant. Exit-2 writes a sentinel flag file (`backlog/.ralph-usage-check-disabled`) to make per-iter warns fire exactly once. `paused` is a terminal state alongside completed/failed for `ralph-status-watch`. No auto-resume by design. Read if porting `usage.py` and pause logic.

#### Task picker / whitelist

- **TASK-65:** `--tasks` whitelist accepts numeric IDs only (regex `^[0-9]+(,[0-9]+)*$`, no `TASK-` prefix); each iteration re-queries status (because deps/states change); whitelist mode replaces the lowest-ID rule with whitelist-order iteration; `tasks_remaining` counts whitelisted To Do IDs only; mutually exclusive with `--prompt-file`. Read if porting task picker.

#### Preflight

- **TASK-58:** 5 ordered fail-fast checks (To Do exists, Ralph-not-running via status+heartbeat-within-15s, devcontainer CLI if requested, `ralph.sh` executable, `bash -n` syntax). Output is exactly one line — `OK RALPH_PATH=<path>` or `ERROR: <reason>`. MUST run against invoker's PWD, never `cd`, never `$0`-relative project paths (the script lives under `~/.claude/skills/...`, the project is elsewhere). Read if porting `preflight.py`.
- **TASK-64:** temp files via `$TMPDIR` (not `/tmp`) for Claude Code sandbox compatibility. Read if porting `preflight.py`.
- **TASK-120:** missing-task detection must anchor on the canonical backlog error line, NOT substring-grep `"not found"` — task descriptions can legitimately contain that phrase. Read if porting `preflight.py` whitelist validation.

#### Watch chain (writer side only — orchestrator emits, watch consumes)

- **TASK-70:** `ralph.sh` writes `iteration_started_at` and structured `errors[]` SOLELY to feed `ralph-status-watch`'s 4 detection rules (finished/crashed/stuck/failed-iter, first-match-wins, priority e>f>g>d). Crashed = heartbeat stale >15s while `state=running`. Stuck = iter elapsed in `[2×timeout, 2×timeout + interval]`. Failed-iter = any `errors[].at` within the last interval. Don't simplify these schema fields away — the watcher has no other signal. Read if porting `status.py` (writer side).

#### Subprocess management / process cleanup

- **TASK-23:** SIGTERM trap kills direct children (timeout/claude) via `pgrep -P $$` but preserves the RUN_LOG `tee` PID so the final log line flushes before exit; status is set to `failed` with `EXIT_REASON=interrupted` (no separate `interrupted` state). Read if porting `tools/claude.py` and the signal handler in the main loop.
- **TASK-37:** Devcontainer exec prefix MUST be an argv list, not a joined string — `devcontainer exec --workspace-folder <path> <cmd...>` breaks via word-splitting when the workspace path contains spaces. Read if porting `tools/claude.py` or any subprocess wrapper that prepends a devcontainer prefix.
- **TASK-35:** Per-iteration timeout value is interpolated into the `timeout` invocation and the seconds calculation; the bash version moved off `awk` to avoid injection when `--timeout` came from the CLI. Re-implementer must validate `--timeout` against a numeric regex before substituting it anywhere. Read if porting CLI arg validation.
- **Commit `4fb8b06`** (Add timeout handling): per-iteration timeout uses GNU `timeout` and treats exit code **124** as "iteration timed out" — the loop logs a warning, sleeps 2s, and continues to the next iteration (does NOT count as a failure for `--on-error`). Read if porting the iteration runner in Python.

#### I/O & streaming contract

- **Commits `3aee486` + `d123f3e` + `1cc007a` + `85c03ab` + `c4d177a`** (stream/verbose churn): the final, load-bearing shape is `<prompt> | claude --print 2>&1 | tee "$OUTFILE"` — NOT command substitution (buffers everything), NOT `--output-format stream-json` (added complexity without reliable real-time output), NOT `--verbose` (floods terminal with tool-call JSON). Output must reach BOTH the terminal AND a temp file so the completion-signal grep can run after the process exits. Read if porting the AI-tool invocation in `tools/claude.py`.

#### Autonomous-mode contract

- **Commit `7e17a07`** (MODE: autonomous prefix): every iteration prompt is prepended with the literal string `MODE: autonomous (Ralph loop iteration <i> of <max>)`. CLAUDE.md keys off the `MODE: autonomous` token to enable the one-task-then-STOP behavior. Re-implementer must preserve the exact prefix string and iteration counter format. Read if porting prompt construction.
- **Commit `90d009a`** (strict task-summary instructions): the autonomous-mode contract in CLAUDE.md mandates a specific `## Task Summary` block as the final output. The Python loop relies on this block being present to confirm a task was actually completed (alongside `<promise>COMPLETE</promise>` for terminal state). Read if porting status derivation.

#### CLI argument contract

- **TASK-33** (`--prompt-file`): when provided, the file's contents REPLACE the hardcoded inner prompt, but `MODE_PREFIX` is still prepended; missing/unreadable file is a hard fail with exit 1 before the loop starts. Both `claude` and `opencode` branches use the same loaded body. Read if porting the prompt builder.
- **TASK-137** (shim → canonical): `RALPH_PROJECT_ROOT` is the contract between the project-root shim and the canonical script — every project-relative path (backlog dir, status file, heartbeat, prompt, CLAUDE.md) resolves via `${RALPH_PROJECT_ROOT:-$SCRIPT_DIR}`, with `$SCRIPT_DIR` as fallback for standalone invocation. The Python port must accept the same env var (or equivalent) so the shim model keeps working. Read if porting path resolution.
- **Commit `205158a`** (resolve symlinks in SCRIPT_DIR): `SCRIPT_DIR` is computed via `pwd -P` after a `cd` to the script's dirname — the `-P` is load-bearing because devcontainer dedup keys on the resolved path; a symlinked invocation would otherwise spin up a duplicate devcontainer. Read if porting `--devcontainer` startup.

#### Exit-path / summary invariant

- **TASK-5:** the run summary (tasks completed, wall time, iterations used, exit reason, per-iteration durations, failure count) MUST print on **every** exit path: clean completion, max-iterations reached, `--on-error stop` abort, and SIGINT/SIGTERM. Exit reasons are the closed set `{all tasks done, max iterations reached, error, interrupted}`. Per-iteration durations are accumulated in an array during the run and printed individually. Read if porting the summary emitter and signal handlers.

### Dependency & runtime constraints

- **Python:** `>=3.14`, pinned in PEP 723 inline metadata. uv handles `uv python install 3.14` automatically.
- **uv:** required runtime dependency. Installed in devcontainer via `Dockerfile.base`. Host-mode bootstraps require user to install uv via OS package manager (`brew install uv`, `pacman -S uv`, `dnf install uv`, or `pipx install uv`); `curl -LsSf https://astral.sh/uv/install.sh | sh` is the last-resort fallback for distros without packaged uv.
- **Third-party deps:** ONLY `pydantic>=2.5`. Nothing else. No rich, no typer, no click, no httpx, no structlog. Discipline lock.
- **Stdlib:** `subprocess`, `json`, `signal`, `argparse`, `pathlib`, `dataclasses`, `re`, `os`, `sys`, `logging`, `tempfile`, `threading`, `queue`, `datetime`.
- **No `pyproject.toml` `[project]` section.** Tool config only. No `uv.lock`. PEP 723 inline metadata is the dependency lock.

### Migration ordering & dependencies

```
US-000 (sync spike) → US-001 (scaffold + StatusFile)
                          ↓
         ┌────────────────┼────────────────┐
         ↓                ↓                ↓
      US-002          US-003            (US-001 also unlocks tests/fixtures/fake_claude.py)
      (helpers)       (core internals)
                          ↓
                      US-004 (claude.py subprocess)
                          ↓
                      US-005 (opencode + entry point + E2E test)
                          ↓
                      US-006 (strangler integration + ralph-init mirror)
                          ↓
                      US-007 (cutover + cleanup + downstream upgrade)
```

US-002 and US-003 are parallelizable after US-001. Everything else is strictly sequential.

### ralph-init impact (R11 mirror surface)

R11 explicitly excludes the canonical ralph-run script from the parity-mirror rule. The orchestrator lives in `~/.claude/skills/ralph-run/scripts/` and is propagated by `ralph-sync`, NOT by `ralph-init`. New projects bootstrapped via `ralph-init` do not get a copy of `ralph_orchestrator.py` (or the `ralph/` package, or the `tests/` directory) in their own tree. This is the architectural decision that bounds the ralph-init impact.

The two ralph-init template files that DO change:

1. **`skills/ralph-init/templates/root/ralph.sh`** — mirrors the live outer shim's strangler dispatch (US-006), then simplifies back to 6 lines after cutover (US-007).
2. **`skills/ralph-init/templates/devcontainer/Dockerfile.base`** — adds uv + Python 3.14 install UNCONDITIONALLY (US-006). New projects regardless of their own chosen language stack now bake the Ralph orchestrator's Python runtime into the base image.

What deliberately does NOT change in ralph-init templates: hooks (`templates/claude/hooks/*.sh`), git hooks (`templates/git-hooks/*`), `init-firewall.sh`, `devcontainer.json`, `CLAUDE.conventions.python.md` (already accurate), `Dockerfile.install.python` (already has uv), the `CLAUDE.md` Project-Specific placeholder section.

---

## 8. Success Metrics

- **5 consecutive clean Python runs** before flipping the strangler default (US-007 gate)
- **5 more consecutive clean runs post-default-flip** before deleting bash (US-007 burn-in)
- **`check_run_clean.py --run-only` exit 0** on each of the 10 gating runs
- **`check_run_clean.py --parity bash.json python.json`** schema parity passes for matched-input runs
- **`pyright` and `ruff check` pass** before every task-reviewer invocation
- **All unit tests + the 1 E2E test pass** in CI-equivalent local runs (`uv run pytest`)
- **Zero behavior regressions** caught by `ralph-reviewer` cumulative review (US-007 final gate before downstream comms)
- **ralph-sync directory propagation works** end-to-end for the Python package (US-000 outcome documented)

---

## 9. Open Questions

These are PRD-level open questions that should be tracked and resolved during implementation or in follow-on tasks. None block PRD acceptance or `/ralph-backlog` fan-out.

1. **Cutover communication channel for downstream Ralph projects.** US-007 mandates documenting upgrade instructions in the task notes. Is there a broader channel (README update, separate `design/upgrade-notes-py-cutover.md` doc, Slack/Discord)? Lean toward README update + task notes, but operator's call.

2. **What does `--prompt-file` do when both `--prompt-file` and `--tasks` are set?** Today's bash treats them as mutually exclusive (the CLI parser rejects both). Python port preserves mutual exclusion via argparse `add_mutually_exclusive_group`. Confirm before US-005.

3. **What happens to `RALPH_STATUS_FILE` / `RALPH_RUN_LOG` env-var overrides post-cutover?** TASK-14 documents these. They MUST be preserved for the Python port to be testable. Confirm during US-001 schema-contract work.

4. **Should `tests/scripts/check_run_clean.py` be reusable for future post-cutover regression detection?** Lean yes — keep it as a long-lived check script in the repo, not a throwaway. Document in US-007.

5. **Does `ralph-sync` need an explicit version handshake for the new Python package?** Today's sync uses content-hash comparison. If sync handles directories correctly (US-000 outcome), no extra work. If sync needs fixing, consider whether to version the package format. Lean toward no version handshake — content hashing is sufficient.

6. **Should `tests/fixtures/fake_claude.py` itself be type-checked?** Yes — it's part of the test surface and should pass `pyright` to catch its own bugs early.

7. **Post-cutover: when do we revisit the deferred §6 features?** Notes in the brainstorm list §6.1 (richer sentinels) and §6.4 (retry classification) as HIGH ROI. Suggest reviewing 2 weeks after cutover, after we have real Python-orchestrator runtime data.

---

## 10. Out-of-Scope Reminders (Reviewer Cross-Checks)

These items are pre-baked invariants the `task-reviewer` and `ralph-reviewer` should check for in every port task:

- **R16 spirit:** task `-d` MUST NOT enumerate historical task IDs. Use bash source line ranges (`skills/ralph-run/scripts/ralph.sh:483-525`) as the spec reference.
- **R11 mirror:** the two ralph-init template files (`templates/root/ralph.sh`, `templates/devcontainer/Dockerfile.base`) MUST be touched in the same task as the live files (US-006, US-007).
- **No scope creep:** if a port task wants to "improve" a piece of behavior (e.g., richer error messages, better logging, optional caching), the reviewer rejects and the improvement gets filed as a separate post-cutover task.
- **Strict-port discipline:** when bash semantics seem suboptimal, the Python port reproduces them anyway. Improvements come later.
- **`feature:ralph-python-refactor` label:** every backlog task fanned out from this PRD MUST carry this label so `/ralph-review name=ralph-python-refactor` picks them all up at the end.

---

*End of PRD. Next step: `/ralph-backlog` against this file to fan out 8 backlog tasks (US-000 through US-007) under `feature:ralph-python-refactor`.*
