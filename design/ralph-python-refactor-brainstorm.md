# Ralph: bash → Python 3.14 + uv refactor

## Context / trigger

The orchestrator (`skills/ralph-run/scripts/ralph.sh`, ~895 lines bash) and three helpers (`preflight.sh`, `wait-heartbeat.sh`, `usage-check.sh`, ~300 lines) carry the most complexity in the project. The bash implementation has accumulated friction:

- **R5 GNU/BSD portability tax** — every shell change has to dodge `sed -i` differences, `date -d` vs `date -j`, `grep -P`, `readlink -f`, etc. Reviewer rule R5 enforces this, which is correct, but the cognitive overhead is real.
- **Status JSON is grep + sed** — 18-field schema parsed by string scraping. Adding a field means touching three writers and N readers; getting them in sync is manual and brittle.
- **Sentinel parsing is string scraping** — single `<promise>COMPLETE</promise>` sentinel + heuristic on `## Task Summary` count. Brittle; can't distinguish "task done" from "task failed, will retry."
- **Retry policy is single-axis** — `--on-error stop|continue|retry` treats a 503 the same as a syntax error.
- **Inspectability is real but eroding** — operators can patch `ralph.sh` mid-session, which is a strength. But the script is too big now to read mid-iteration without losing context.

The Claude Code skill ecosystem is mostly markdown + shell scripts, so until recently bash was the path of least resistance. With `uv` + PEP 723 inline metadata, Python now has the same "source IS the artifact" distribution story as bash: no build, no CI, no install — `/ralph-sync` propagates the .py file the same way it propagates the .sh file today.

## Direction (locked, via 7 brainstorm questions)

| # | Decision | Locked option | Rationale |
|---|---|---|---|
| 1 | Migration strategy | **Strangler-fig behind env var flag** (`RALPH_IMPL=python\|bash`) | Both implementations coexist; rollback is one env var. The autonomous loop is too load-bearing to risk a big-bang regression. |
| 2 | Scope of the rewrite itself | **Strict port, features later** | Python orchestrator must produce byte-identical status JSON, accept same flags, emit same logs. New features (§6.1 sentinels, §6.4 retry classification, §6.2 external reviewer) are post-port tasks. Isolates language-change risk from behavior-change risk. |
| 3 | Dependency budget | **Stdlib + pydantic** | One PyPI dep (pydantic≥2.5) for `StatusFile` schema validation + JSON round-tripping. Everything else (`subprocess`, `signal`, `argparse`, `pathlib`, `dataclasses`, `json`) is stdlib. PEP 723 metadata is one line. |
| 4 | Helper scripts in scope | **Port `preflight.sh`, `wait-heartbeat.sh`, `usage-check.sh`** | These are called from the orchestrator and benefit from shared types and logic. `sync.sh` (called from skill markdown) and `utc-to-moscow.sh` (5-line awk one-liner) stay bash. Hooks ALL stay bash. |
| 5 | Cutover gate | **5 consecutive clean Ralph runs on Python** | Concrete and fast. "Clean" = status JSON readable by `ralph-status` throughout, no `errors[]` entries during the run, exit code 0, heartbeat fresh, no process leaks. Default flips on the 5th success. Bash deleted 5 more runs later. |
| 6 | Test depth on day one | **Unit + fake-claude E2E** | Pytest units for: signal parsing, `StatusFile` pydantic schema (with golden-file comparison vs bash output), retry classifier, usage-check parser, task picker. Plus ONE E2E test that runs the orchestrator against a fake `claude-code` shim emitting canned stream-json. Catches subprocess/signal/heartbeat race bugs that unit tests miss. |
| 7 | Type checking | **`pyright` in strict mode** | Faster than mypy (~5s vs ~30s), strict mode catches most real bugs, plays well with VS Code. Run as `uv run pyright` in a check step before `task-reviewer`. |

## What flows where (sketched)

```
                   ┌─────────────────────────────┐
                   │  /ralph.sh  (shim, bash)    │
                   │  6 lines; reads RALPH_IMPL  │
                   └──────────┬──────────────────┘
                              │
                  RALPH_IMPL=?│
                  ┌───────────┴───────────┐
            bash  │                       │  python
                  ▼                       ▼
   ┌──────────────────────┐    ┌──────────────────────────────────┐
   │ ralph.sh             │    │ ralph_orchestrator.py            │
   │ (~895 lines, today)  │    │ + ralph/ package                 │
   │                      │    │ + uv run + PEP 723 inline deps   │
   └──────────────────────┘    └──────────────────────────────────┘
                              │
                              │ same JSON contract
                              ▼
              ┌──────────────────────────────────┐
              │ backlog/.ralph-status.json       │
              │ backlog/.ralph-heartbeat         │
              │ backlog/.ralph-run.log           │
              └──────────────────────────────────┘
                              ▲
                              │ read by
   ┌──────────────────────────┴───────────────────────────────────┐
   │ ralph-status, ralph-status-watch, ralph-stop, external tools │
   └──────────────────────────────────────────────────────────────┘
```

The dual-implementation period (steps 5–6 of the cutover) is the load-bearing safety mechanism. External readers (`ralph-status`, etc.) don't know or care which implementation wrote the status JSON; the contract is the on-disk format.

## Proposed package layout (under the strict-port lock)

```
skills/ralph-run/scripts/
├── ralph.sh                      # unchanged: existing bash impl
├── ralph_orchestrator.py         # entry point; PEP 723 inline metadata
├── ralph/                        # package (sibling import via sys.path[0])
│   ├── __init__.py
│   ├── status.py                 # StatusFile pydantic model, atomic writes
│   ├── heartbeat.py              # threading.Thread daemon; touch every 5s
│   ├── tools/
│   │   ├── __init__.py           # Tool protocol
│   │   ├── claude.py             # claude-code Popen + tee + signal parse
│   │   └── opencode.py           # opencode Popen + tee + signal parse
│   ├── signals.py                # <promise>COMPLETE</promise> + Task Summary parse
│   ├── usage.py                  # ccusage wrapper; pause decision
│   ├── tasks.py                  # backlog CLI wrapper, picker
│   ├── preflight.py              # ports preflight.sh
│   ├── wait_heartbeat.py         # ports wait-heartbeat.sh
│   └── usage_check.py            # ports usage-check.sh; preserves exit-code contract
└── tests/
    ├── conftest.py               # pytest fixtures (tmpdir, fake-claude shim)
    ├── test_status.py            # golden-file: pydantic output == bash output
    ├── test_signals.py
    ├── test_usage_check.py
    ├── test_tasks.py
    └── test_e2e_fake_claude.py   # fake claude-code emits canned stream-json
```

PEP 723 inline metadata on `ralph_orchestrator.py`:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["pydantic>=2.5"]
# ///
```

The `ralph/` package is found via `sys.path[0]` (script's parent dir) — no `pyproject.toml`, no `uv.lock`, no `uv sync`. PEP 723 + sibling package is sufficient. Tests live under `skills/ralph-run/tests/` to keep the skill self-contained.

## ralph-init impact (R11 mirror surface)

The refactor's mirror set extends to ralph-init templates — but the surface is small because **R11 explicitly excludes the canonical ralph-run script from parity**. The orchestrator lives in `~/.claude/skills/ralph-run/scripts/` and is propagated by `ralph-sync`, NOT by `ralph-init`. New projects do not get a copy of `ralph_orchestrator.py` (or the `ralph/` package, or the `tests/` directory) in their own tree. This is the architectural decision that keeps the ralph-init impact bounded.

### Template changes (2 files)

1. **`skills/ralph-init/templates/root/ralph.sh`** — the 6-line outer shim grows to ~10 lines with the strangler dispatch (see Q6 "Strangler flag location"). During the dual-running period, defaults to bash and dispatches to Python via `RALPH_IMPL=python`. At cutover: drop the bash branch, keep only the Python exec.

2. **`skills/ralph-init/templates/devcontainer/Dockerfile.base`** — add uv + Python 3.14 install **UNCONDITIONALLY** (not gated on the project's chosen language). The orchestrator's runtime becomes part of the base contract regardless of whether the project itself is Go, Node, docs, or anything else. Two lines:

   ```dockerfile
   COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
   RUN uv python install 3.14
   ```

   This crosses an abstraction layer in the existing template structure (today's `Dockerfile.base` is language-agnostic; language-specific stages live in `lang/Dockerfile.install.*`). Worth an inline comment in the template explaining WHY uv is unconditional ("required by Ralph orchestrator regardless of project language").

### Things deliberately UNCHANGED

- `templates/root/CLAUDE.conventions.python.md` — already documents the uv-only conventions for projects whose own language is Python. No edit.
- `templates/devcontainer/lang/Dockerfile.install.python` — already copies uv via `COPY --from=ghcr.io/astral-sh/uv:latest`. No edit. Project-language-specific stages stay scoped.
- All Claude hooks (`templates/claude/hooks/*.sh`) — stay bash per the lock.
- All git hooks (`templates/git-hooks/*`) — stay bash.
- `templates/devcontainer/init-firewall.sh` — stays bash (iptables/ipset belongs there).
- `templates/devcontainer/devcontainer.json` — no change.
- `templates/root/CLAUDE.md` Project-Specific section — placeholder for end users to fill in; unchanged by refactor.
- 4 other `lang/Dockerfile.*` files (go, node, docs, plus the Python language stage) — irrelevant; they're project-runtime stages, not orchestrator runtime.

### Side effects (handle in the implementation tasks)

- **`ralph-sync` directory handling.** Today's sync handles files in `skills/ralph-run/scripts/`. The Python orchestrator adds a `ralph/` package subdirectory and a `tests/` subdirectory. Sync must propagate these correctly. This is risk register item #6 — verify via a 5-minute spike BEFORE Task 1. If sync needs fixing, that's a precondition task (Task 0).
- **`skills/ralph-init/SKILL.md` Prerequisites note.** For host-mode (devcontainer=false) bootstraps, the user needs uv installed on the host before `/ralph-run` works. One paragraph in ralph-init's SKILL.md explaining `curl -LsSf https://astral.sh/uv/install.sh | sh`.
- **Existing projects need re-bootstrap or hand-patch.** After cutover, every existing Ralph project (not just this one) needs `ralph-init upgrade` to re-apply the new templates, OR a manual patch of the two affected files. Document this explicitly in the Task 7 (cleanup) acceptance criteria so the cutover communication includes upgrade instructions.

## Migration plan (4 stages)

### Stage 1: scaffold (3–4 days)
- Add `ralph_orchestrator.py` (entry point), `ralph/` package skeleton, `tests/` skeleton with conftest.
- Implement `StatusFile` pydantic model with golden-file test: feed sample bash output JSON → parse → re-serialize → byte-equal to input. This is the contract enforcement.
- Implement `signals.py` (parse `<promise>COMPLETE</promise>` and `## Task Summary` block) with golden-file tests.
- No orchestrator behavior yet. Just contracts.

### Stage 2: port internals (1 week)
- Port `tasks.py` (backlog CLI wrapper).
- Port `usage.py` + `usage_check.py` (preserving exit-code contract 0/1/2).
- Port `preflight.py` (preconditions).
- Port `wait_heartbeat.py` (10×1s poll).
- Port `heartbeat.py` (daemon thread touching every 5s with clean-shutdown drain).
- Port `tools/claude.py` (subprocess.Popen + tee-equivalent + sentinel scanning in real-time).
- Wire entry point: arg parsing (argparse, exact flag names) → preflight → orchestrate.

### Stage 3: dual-running window (1–2 weeks)
- Strangler shim: outer `/ralph.sh` reads `RALPH_IMPL`; defaults to bash. Inner `skills/ralph-run/scripts/ralph.sh` untouched.
- `/ralph-run` skill grows an `impl` parameter (default `bash`) that sets `RALPH_IMPL`.
- **R11 mirror to ralph-init template:** `skills/ralph-init/templates/root/ralph.sh` updated to match the live outer shim (the dispatch logic). Same task as the live shim change.
- **Devcontainer Dockerfile.base mirror:** `skills/ralph-init/templates/devcontainer/Dockerfile.base` gets uv + Python 3.14 install (unconditional, not language-gated). Same task as the live Dockerfile change.
- **`ralph-sync` directory handling spike** (Task 0 precondition): verify sync.sh propagates `ralph/` subdirectory and `tests/` subdirectory correctly. Fix sync.sh if not.
- **`skills/ralph-init/SKILL.md` Prerequisites note:** add one-paragraph mention that host-mode bootstraps require uv on the host.
- Run real tasks with `RALPH_IMPL=python` opt-in. Count clean runs.

### Stage 4: cutover (1 day + 2 weeks bash burn-in)
- Flip default to `RALPH_IMPL=python` after 5 clean runs (both in the live outer shim AND in `skills/ralph-init/templates/root/ralph.sh`).
- Keep inner `ralph.sh` bash version available for 5 more clean runs as rollback path.
- Delete inner bash `ralph.sh` + bash helpers (`preflight.sh`, `wait-heartbeat.sh`, `usage-check.sh`) after 10 total clean runs.
- Outer shim (live + template) simplifies back to 6 lines pointing only at Python.
- Update `/ralph-run` skill to drop the `impl` parameter.
- **Communicate to other Ralph projects:** anyone with an existing project must run `ralph-init upgrade` to re-apply the new shim + Dockerfile.base, OR hand-patch those two files. Document in the cutover task's notes section.

## Risk register (ranked by likelihood × blast radius)

1. **Process tree kills.** `pkill -TERM -P` in bash needs `os.killpg(os.getpgid(pid), signal.SIGTERM)` + `Popen(..., preexec_fn=os.setpgrp)` in Python. Symptom: zombie claude-code processes after `/ralph-stop`. **Mitigation:** explicit unit test for `tools/claude.py` that spawns a sleep child and asserts it's gone after stop signal.
2. **Status JSON atomicity.** External readers MUST never see partial JSON. **Mitigation:** all writes via `tempfile.NamedTemporaryFile` in same dir + `os.replace()`. Wrap in a `StatusFile.write_atomic()` helper that's the only path to disk.
3. **Heartbeat-on-shutdown race.** Daemon thread killed mid-write leaves stale or truncated heartbeat. **Mitigation:** thread holds a `threading.Event`; main thread sets event and `thread.join(timeout=10)` before exit. Status writer also flushes a final "completed/failed" state after the join.
4. **Subprocess output streaming.** `proc.communicate()` blocks until exit; useless for real-time sentinel detection. **Mitigation:** `Popen(stdout=PIPE, bufsize=1, text=True)` + `for line in proc.stdout` reader thread, push to a queue, scan + tee in main thread.
5. **Pydantic schema drift.** If pydantic model adds a field, bash readers and old Python readers can't parse the new JSON. **Mitigation:** strict-port stage forbids schema additions. Post-cutover schema changes get a TASK and a parallel-readability check.
6. **`/ralph-sync` and directory structure.** Today `sync.sh` copies files; `ralph/` is a directory. **Mitigation:** verify before stage 1 that sync handles directories under skill scripts; fix sync if not.
7. **Devcontainer cold start.** First `uv run` downloads pydantic + creates venv (~1–2s). **Mitigation:** Dockerfile pre-warms the cache: `RUN uv run --no-cache <empty pydantic import>` during build.
8. **PEP 723 + sibling package import.** `ralph_orchestrator.py` doing `import ralph` — does PEP 723's sys.path setup pick up the script's parent? **Mitigation:** verify in a 5-minute spike before stage 1 commits.

## Resolved during brainstorm (was "open"; now locked)

All six items below were walked one-at-a-time and locked. They are part of the contract for the implementer.

### Q1 — "Clean run" definition (cutover gate)
**Locked:** a clean run requires ALL of:
1. `state=completed`
2. `exit_code=0`
3. `errors[]` empty
4. **≥1 task moved To Do → Done during the run** (gate must exercise the real work path; empty-backlog runs don't count toward the 5)
5. Heartbeat fresh THROUGHOUT the run: sampling pass during the run polls heartbeat every 5s, max age never exceeded 15s
6. No leftover `claude-code` / `python` / `uv` processes after the orchestrator exits

Codify as `tests/scripts/check_run_clean.py`, two modes:
- `--run-only` — checks 1–6 against a single completed run, exit 0 = clean.
- `--parity bash_status.json python_status.json` — schema parity check (key set, key order; values may differ for timestamps/pids).

The 5-clean-runs gate is "5 successive `--run-only` invocations that exit 0." Mechanical, not judgment.

### Q2 — Fake claude-code shim
**Locked:** `tests/fixtures/fake_claude.py`. Drop-in replacement for `claude-code` binary. Invocation is identical (ignores `--model`, `--effort`, `--print`; reads prompt from stdin). Extracts task ID from the prompt. Behavior controlled by `FAKE_CLAUDE_MODE` env var:

- `success` (default): emits canned "I'm doing things" text, **calls `backlog task edit <id> -s Done`** so the orchestrator's done-task diff sees real movement, emits `## Task Summary` block referencing the actual task ID, emits `<promise>COMPLETE</promise>`, exits 0.
- `task_done_no_summary`: same as success but skips the Summary block (tests heuristic robustness).
- `fail`: emits error to stderr, exits 1.
- `hang`: sleeps forever (tests timeout handling).

Used by both unit tests (mock claude_code subprocess invocation) and the one E2E test (real subprocess with fake binary). Risk acknowledged: fake's correctness becomes a test dependency on the `backlog` CLI; mitigated by a smoke test that verifies fake actually edits the backlog before relying on it.

### Q3 — Logging strategy
**Locked:** use `print()` during strict port for anything that matches today's bash stdout messages (iteration markers, status transitions, paused-due-to lines). Use `logging.debug()` for new Python-internal diagnostics. The on-disk format of `backlog/.ralph-run.log` is unchanged because `tools/claude.py` writes child stdout to both file and stdout-scanner (tee equivalent). Post-cutover migration to all-`logging` is a separate concern, NOT in this refactor.

### Q4 — CLI flag parity
**Locked:** exact bash flag names via argparse. Use `argparse.ArgumentParser.parse_intermixed_args()` so flag/positional ordering matches bash flexibility (e.g., `ralph 10 --tool claude` works as well as `ralph --tool claude 10`). Disable argparse's auto short-flag inference (no `-t` for `--tool`) since bash doesn't have them. Add a unit test that exercises 5–6 different orderings. NO new short flags during the port.

### Q5 — Lint config location
**Locked:** `pyproject.toml` at repo root, tool-config only (no `[project]` section, no package declaration). Holds `[tool.ruff]` and `[tool.pyright]` sections. Sketch:

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

GitHub language detection will flip the repo to Python on the language bar. This is directionally accurate after the refactor lands and acknowledged as an early-signal cost.

### Q6 — Strangler flag location
**Locked:** dispatch in the OUTER shim (`/Users/paul/Private/Projects/ai/ralph/ralph.sh`), not the inner orchestrator. Outer shim becomes ~10 lines:

```bash
#!/bin/bash
CANONICAL_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ralph-run/scripts"
if [[ "${RALPH_IMPL:-bash}" == "python" ]]; then
  exec uv run "$CANONICAL_DIR/ralph_orchestrator.py" "$@"
fi
RALPH_PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)" \
  exec "$CANONICAL_DIR/ralph.sh" "$@"
```

Inner `skills/ralph-run/scripts/ralph.sh` is untouched during the port. `/ralph-run` skill grows an `impl=python|bash` parameter (default `bash`), exports `RALPH_IMPL=<value>` in the launch env. Cutover flips skill default to `python`. Stage 4 cleanup deletes inner `ralph.sh` and simplifies outer shim back to 6 lines pointing only at Python.

## Appendix: Historical context (reference only, NOT contract)

This appendix lists historical backlog tasks that document **load-bearing invariants** — behaviors that would be easy to "simplify away" during the port if the Python implementer didn't know WHY they exist. The current bash code IS the spec for the port; this appendix is the supplementary "why."

**Discipline (R16 spirit):** individual port tasks MUST NOT enumerate these task IDs in their `-d`. The port-task spec is the bash source line range. This appendix exists only so that PRD/reviewer/implementer can resolve ambiguity ON DEMAND. If a port task's bash range is unambiguous, no historical-task reading is needed.

### Status JSON schema
- TASK-6: foundational `.ralph-status.json` contract — fields `pid, started_at, state (running/completed/failed), iteration, max_iterations, tool, tasks_done, tasks_remaining, current_task, last_iteration_duration, elapsed, errors[], completed_at, exit_code`; `tasks_done` is the diff of Done IDs before/after each iteration (the DONE_BEFORE/DONE_AFTER channel); written at every lifecycle point. Read if porting `status.py`.
- TASK-13: `current_task` is derived from the `To Do` query output (`grep -o 'TASK-[0-9]*' | head -1`) at iteration *start*, not from `In Progress` — the agent hasn't moved the task yet. Read if porting `status.py` / task picker.
- TASK-24: `current_task` must be re-queried from `In Progress` at iteration *end* — otherwise it's stale immediately. Two distinct writes per iteration, on purpose. Read if porting `status.py`.
- TASK-14: status/log file paths must be overridable via `RALPH_STATUS_FILE` / `RALPH_RUN_LOG` env vars so tests don't clobber real state. Read if porting `status.py`.
- TASK-70: status schema additions `iteration_started_at` (ISO, written at iter top) and `errors[]` as `{iteration, at, message}` objects (NOT bare strings) exist specifically so `ralph-status-watch` can detect stuck/failed-iter events stateless-ly. Read if porting `status.py` and `watch.py`. **(See also: Watch chain section below for the consumer-side detection rules.)**
- TASK-42: `elapsed` in the file is stale by design (only written at iteration boundaries) — readers compute live `elapsed = now - started_at` when `state=running`. Read if porting `status.py` consumers.
- TASK-75: all timestamps in JSON stay UTC with `Z` suffix; timezone conversion happens only in display skills. Do not change the on-disk format. Read if porting `status.py`.

### Heartbeat
- TASK-50: heartbeat is a backgrounded subshell that `touch`es `backlog/.ralph-heartbeat` every 5s and self-terminates via `kill -0 $parent` polling — this is the SIGKILL-survivable liveness signal. EXIT trap must kill the HB child and remove the file. Read if porting `heartbeat.py` and process cleanup.
- TASK-53: freshness check uses `stat -f %m` (BSD) / `stat -c %Y` (GNU) + arithmetic, NOT `find -mmin -0.25` (BSD `find` truncates fractional minutes; silently always-false). The 15s threshold is 3× the 5s touch interval. Read if porting `heartbeat.py`.
- TASK-77: `wait-heartbeat.sh` is a separate script (not inline) with a fixed 10×1s poll window and 15s freshness criterion for first-detection after launch; exists as a script to fit narrow bash-allowlist permissions. Read if porting `wait_heartbeat.py`.
- TASK-43: double-run guard reads `pid` from the status JSON and uses `kill -0` — this is the explicit anti-double-start contract, moved from the skill into `ralph.sh` so it's enforced regardless of invoker. Read if porting `ralph.py` startup.

### Sentinel parsing
- TASK-18: per-iteration check counts `^## Task Summary$` blocks in the captured output (anchored regex to avoid matching quoted CLAUDE.md text). Expected count = 1, except when `<promise>COMPLETE</promise>` is present (legitimate 0-block case). Warning-only, not fatal — observability of the one-task-per-iteration invariant. Read if porting `iteration.py`.
- TASK-1: agent invocation must be `timeout ... claude <<< $PROMPT | tee` (heredoc/process-sub, NOT `echo $PROMPT | timeout ... | tee`) so `PIPESTATUS[0]` captures the AI tool's exit code, not `echo`'s. Read if porting subprocess invocation.

### Usage-cap pause
- TASK-135: `usage-check.sh` contract is exit-code-based — 0=ok, 1=pause (prints `block_end_in_<rem>min_below_<buffer>min_buffer`), 2=cannot measure. The 5 `paused_*` JSON fields (`paused_reason`, `paused_buffer_min`, `paused_remaining_min`, `paused_block_end_time`, `paused_at`) all exist for a reason: `paused_remaining_min` is what the check saw at trip time, `paused_block_end_time` is the absolute ccusage timestamp for resume planning — neither is redundant. Exit-2 writes a sentinel flag file (`backlog/.ralph-usage-check-disabled`) to make per-iter warns fire exactly once. `paused` is a terminal state alongside completed/failed for `ralph-status-watch`. No auto-resume by design. Read if porting `usage.py` and pause logic.

### Task picker / whitelist
- TASK-65: `--tasks` whitelist accepts numeric IDs only (regex `^[0-9]+(,[0-9]+)*$`, no `TASK-` prefix); each iteration re-queries status (because deps/states change); whitelist mode replaces the lowest-ID rule with whitelist-order iteration; `tasks_remaining` counts whitelisted To Do IDs only; mutually exclusive with `--prompt-file`. Read if porting task picker.

### Preflight
- TASK-58: 5 ordered fail-fast checks (To Do exists, Ralph-not-running via status+heartbeat-within-15s, devcontainer CLI if requested, `ralph.sh` executable, `bash -n` syntax). Output is exactly one line — `OK RALPH_PATH=<path>` or `ERROR: <reason>`. MUST run against invoker's PWD, never `cd`, never `$0`-relative project paths (the script lives under `~/.claude/skills/...`, the project is elsewhere). Read if porting `preflight.py`.
- TASK-64: temp files via `$TMPDIR` (not `/tmp`) for Claude Code sandbox compatibility. Read if porting `preflight.py`.
- TASK-120: missing-task detection must anchor on the canonical backlog error line, NOT substring-grep `"not found"` — task descriptions can legitimately contain that phrase. Read if porting `preflight.py` whitelist validation.

### Watch chain (writer side only — orchestrator emits, watch consumes)
- TASK-70: `ralph.sh` writes `iteration_started_at` and structured `errors[]` SOLELY to feed `ralph-status-watch`'s 4 detection rules (finished/crashed/stuck/failed-iter, first-match-wins, priority e>f>g>d). Crashed = heartbeat stale >15s while `state=running`. Stuck = iter elapsed in `[2×timeout, 2×timeout + interval]`. Failed-iter = any `errors[].at` within the last interval. Don't simplify these schema fields away — the watcher has no other signal. Read if porting `status.py` (writer side).

### Subprocess management / process cleanup
- TASK-23: SIGTERM trap kills direct children (timeout/claude) via `pgrep -P $$` but preserves the RUN_LOG `tee` PID so the final log line flushes before exit; status is set to `failed` with `EXIT_REASON=interrupted` (no separate `interrupted` state). Read if porting `tools/claude.py` and the signal handler in the main loop.
- TASK-37: Devcontainer exec prefix MUST be an argv list, not a joined string — `devcontainer exec --workspace-folder <path> <cmd...>` breaks via word-splitting when the workspace path contains spaces. Read if porting `tools/claude.py` or any subprocess wrapper that prepends a devcontainer prefix.
- TASK-35: Per-iteration timeout value is interpolated into the `timeout` invocation and the seconds calculation; the bash version moved off `awk` to avoid injection when `--timeout` came from the CLI. Re-implementer must validate `--timeout` against a numeric regex before substituting it anywhere. Read if porting CLI arg validation.
- Commit `4fb8b06` (Add timeout handling): per-iteration timeout uses GNU `timeout` and treats exit code **124** as "iteration timed out" — the loop logs a warning, sleeps 2s, and continues to the next iteration (does NOT count as a failure for `--on-error`). Read if porting the iteration runner in Python.

### I/O & streaming contract
- Commits `3aee486` + `d123f3e` + `1cc007a` + `85c03ab` + `c4d177a` (stream/verbose churn): the final, load-bearing shape is `<prompt> | claude --print 2>&1 | tee "$OUTFILE"` — NOT command substitution (buffers everything), NOT `--output-format stream-json` (added complexity without reliable real-time output), NOT `--verbose` (floods terminal with tool-call JSON). Output must reach BOTH the terminal AND a temp file so the completion-signal grep can run after the process exits. Read if porting the AI-tool invocation in `tools/claude.py`.

### Autonomous-mode contract
- Commit `7e17a07` (MODE: autonomous prefix): every iteration prompt is prepended with the literal string `MODE: autonomous (Ralph loop iteration <i> of <max>)`. CLAUDE.md keys off the `MODE: autonomous` token to enable the one-task-then-STOP behavior. Re-implementer must preserve the exact prefix string and iteration counter format. Read if porting prompt construction.
- Commit `90d009a` (strict task-summary instructions): the autonomous-mode contract in CLAUDE.md mandates a specific `## Task Summary` block as the final output. The Python loop relies on this block being present to confirm a task was actually completed (alongside `<promise>COMPLETE</promise>` for terminal state). Read if porting status derivation.

### CLI argument contract
- TASK-33 (`--prompt-file`): when provided, the file's contents REPLACE the hardcoded inner prompt, but `MODE_PREFIX` is still prepended; missing/unreadable file is a hard fail with exit 1 before the loop starts. Both `claude` and `opencode` branches use the same loaded body. Read if porting the prompt builder.
- TASK-137 (shim → canonical): `RALPH_PROJECT_ROOT` is the contract between the project-root shim and the canonical script — every project-relative path (backlog dir, status file, heartbeat, prompt, CLAUDE.md) resolves via `${RALPH_PROJECT_ROOT:-$SCRIPT_DIR}`, with `$SCRIPT_DIR` as fallback for standalone invocation. The Python port must accept the same env var (or equivalent) so the shim model keeps working. Read if porting path resolution.
- Commit `205158a` (resolve symlinks in SCRIPT_DIR): `SCRIPT_DIR` is computed via `pwd -P` after a `cd` to the script's dirname — the `-P` is load-bearing because devcontainer dedup keys on the resolved path; a symlinked invocation would otherwise spin up a duplicate devcontainer. Read if porting `--devcontainer` startup.

### Exit-path / summary invariant
- TASK-5: the run summary (tasks completed, wall time, iterations used, exit reason, per-iteration durations, failure count) MUST print on **every** exit path: clean completion, max-iterations reached, `--on-error stop` abort, and SIGINT/SIGTERM. Exit reasons are the closed set `{all tasks done, max iterations reached, error, interrupted}`. Per-iteration durations are accumulated in an array during the run and printed individually. Read if porting the summary emitter and signal handlers.

---

## Distilled for ralph-task (Phase 4 hand-off)

Per project R16: tasks consuming this brainstorm should NOT reference this file in `-d`. The block below is the verbatim contract for the implementer. Multi-task feature (≥5 tasks); recommend creating via `ralph-prd` from this distillation rather than `ralph-task` directly.

### Direction
Port `skills/ralph-run/scripts/ralph.sh` and three helpers (`preflight.sh`, `wait-heartbeat.sh`, `usage-check.sh`) to Python 3.14 + uv with PEP 723 inline deps. Strict port — byte-identical status JSON, same flags, same logs — strangler-fig behind `RALPH_IMPL` env var with bash as default. New features (richer sentinels, retry classification, external reviewer) are post-port follow-ups, NOT bundled.

### Locked decisions (do not re-litigate)
- Single PyPI dep: `pydantic>=2.5`. Stdlib for everything else.
- Package layout: `ralph_orchestrator.py` (PEP 723 entry) + `ralph/` sibling package + `tests/`. `pyproject.toml` at repo root holds `[tool.ruff]` and `[tool.pyright]` config only (no package declaration, no `[project]` section). NO `uv.lock`.
- Strangler flag: `RALPH_IMPL=bash|python` (env var) and `impl=python|bash` (skill param), default `bash` until cutover. Dispatch in the OUTER shim (`/ralph.sh`), NOT the inner orchestrator. Inner `ralph.sh` is untouched during the port.
- Cutover gate: 5 consecutive clean runs on `RALPH_IMPL=python`. "Clean" = state=completed AND exit_code=0 AND empty errors[] AND **≥1 task moved To Do→Done during the run** AND heartbeat fresh throughout (sampled every 5s during run, max age never exceeded 15s) AND no leftover claude-code/python/uv processes after exit. Codified as `tests/scripts/check_run_clean.py --run-only`.
- Test depth: unit + ONE fake-claude E2E. pytest. Fake claude-code shim at `tests/fixtures/fake_claude.py`. **Fake actually edits the backlog** via `backlog task edit <id> -s Done` so the orchestrator's done-task diff is exercised end-to-end. Behavior modes via `FAKE_CLAUDE_MODE`: success (default), task_done_no_summary, fail, hang.
- Type checker: `pyright --strict`, runs before `task-reviewer`.
- Logging: `print()` for messages matching today's bash stdout (iteration markers, status transitions). `logging.debug()` for new Python-internal diagnostics. On-disk `backlog/.ralph-run.log` format unchanged. NO migration to all-`logging` during the strict port.
- CLI flag parity: exact bash flag names. Use `argparse.parse_intermixed_args()` for flexible ordering. NO auto short-flag inference (no `-t`, etc.). NO new short flags.
- Helpers in scope: `preflight.sh`, `wait-heartbeat.sh`, `usage-check.sh`. NOT in scope: `sync.sh`, `utc-to-moscow.sh`, hooks (all stay bash).
- Hooks DO NOT change. They remain bash because Claude Code invokes them per-tool-call and bash startup is ~5ms vs Python's ~80ms.
- Bash `ralph.sh` (inner orchestrator + bash helpers `preflight.sh`/`wait-heartbeat.sh`/`usage-check.sh`) is deleted only after 5 MORE clean runs post-cutover (10 total). Outer shim simplifies back to 6 lines pointing only at Python.

### Scope cuts (explicit non-goals)
- No schema changes to `backlog/.ralph-status.json`. Same 18 fields, same key order.
- No new CLI flags. No flag renames.
- No new sentinels. `<promise>COMPLETE</promise>` and `## Task Summary` parsing unchanged.
- No new retry policy. `--on-error stop|continue|retry` semantics preserved.
- No worktree isolation. No external reviewer. No notifications. No `--plan` mode. All deferred to post-port tasks.
- No hook changes. R5 (GNU/BSD) still applies to surviving bash.

### Implementation checklist (≥5 task shapes; PRD-worthy)

0. **Precondition: `ralph-sync` directory-handling spike.** Verify `.claude/skills/ralph-sync/sync.sh` correctly propagates files in nested subdirectories under `skills/ralph-run/scripts/` (specifically: `ralph/` package and `tests/` directory). 5-minute spike: create a throwaway `skills/ralph-run/scripts/spike/dummy.txt`, run `ralph-sync classify` then `apply`, verify `~/.claude/skills/ralph-run/scripts/spike/dummy.txt` appears. If sync drops directories, fix sync.sh to recurse before Task 1. If sync handles them already, mark this task Done with a one-line note and proceed. Blocks Task 1.

1. **Scaffold + StatusFile contract.** Add `ralph_orchestrator.py` with PEP 723, `ralph/__init__.py`, `tests/conftest.py`, `tests/test_status.py`. Pydantic `StatusFile` model with golden-file round-trip test (sample bash output JSON → parse → serialize → byte-equal). Add `pyrightconfig.json` strict, `.ruff.toml`. Verify PEP 723 + sibling package imports work via spike.

2. **Port helpers.** Port `usage_check.py` (preserve exit codes 0/1/2 with same stdout). Port `preflight.py` (preconditions). Port `wait_heartbeat.py` (10×1s poll). Unit tests for each. Bash helpers stay in place; Python helpers are unused until Stage 3.

3. **Port core internals.** Port `signals.py`, `tasks.py`, `heartbeat.py`, `usage.py`, `tools/__init__.py` (Tool protocol). Unit tests for each. Golden-file tests for signal parsing.

4. **Port claude-code subprocess management.** `tools/claude.py` with Popen + tee + sentinel scanner + signal handling + process-group cleanup. Unit test: spawn fake-claude sleep child, send SIGTERM to orchestrator, assert child gone within 5s.

5. **Port opencode + wire entry point.** `tools/opencode.py`. argparse with exact bash flag names. Entry point: parse args → preflight → orchestrate loop → final status write. Add E2E test against `tests/fixtures/fake_claude.py`.

6. **Strangler integration + ralph-init mirror.** Update outer `ralph.sh` shim to read `RALPH_IMPL`. Update `skills/ralph-run/SKILL.md` to accept `impl=python|bash` (default `bash`); export `RALPH_IMPL` before launching. Update live devcontainer `Dockerfile.base` to add uv + Python 3.14 install unconditionally (NOT gated on project language). **R11 mirror at the same time:** `skills/ralph-init/templates/root/ralph.sh` mirrors the live outer shim's dispatch logic; `skills/ralph-init/templates/devcontainer/Dockerfile.base` mirrors the live unconditional uv install. Add one-paragraph Prerequisites note to `skills/ralph-init/SKILL.md` about host-mode uv requirement. Verify `/ralph-sync` correctly propagates `ralph/` subdirectory and `tests/` subdirectory under skill scripts; if not, fix sync.sh (precondition Task 0 may absorb this).

7. **Cutover + cleanup + downstream upgrade.** Run 5 clean cycles on Python (operator-driven). Flip default `RALPH_IMPL=python` in `/ralph-run` SKILL.md, in the live outer `ralph.sh` shim, AND in `skills/ralph-init/templates/root/ralph.sh`. Run 5 more clean cycles. Delete inner bash `ralph.sh` + bash helpers (`preflight.sh`, `wait-heartbeat.sh`, `usage-check.sh`). Outer shim (live + template) simplifies back to 6 lines pointing only at Python. Update CLAUDE.md Project-Specific section to note bash orchestrator is gone. **Communicate downstream:** existing Ralph projects must run `ralph-init upgrade` to re-apply the new shim + Dockerfile.base, or hand-patch those two files. Include explicit upgrade instructions in the task notes.

### Acceptance criteria sketch (per task; not exhaustive)

- Task 0: ralph-sync spike completed; either sync handles nested directories (Done with note) or sync.sh fixed to recurse with unit/manual test demonstrating directory propagation.
- Task 1: `tests/test_status.py` passes; golden-file round-trip byte-equal.
- Task 2: `usage_check.py --buffer 0` returns exit 0 with no output; `--buffer 9999` returns exit 1 with `block_end_in_*` line; bash and Python implementations produce identical exit codes and stdout for same inputs.
- Task 3: Each helper has ≥1 unit test; pyright strict passes.
- Task 4: E2E test: orchestrator launches fake-claude shim, receives sentinel, exits clean, status JSON matches golden.
- Task 5: orchestrator entry point completes one fake-claude iteration; status JSON has `state=completed`, `exit_code=0`, empty `errors[]`.
- Task 6: `RALPH_IMPL=python /ralph-run` launches Python orchestrator and runs to completion against a real backlog task in the devcontainer.
- Task 7: bash orchestrator deleted; `git log` shows no shim references after deletion; CLAUDE.md updated.

### Reviewer cross-checks (for `ralph-review` after the feature is merged)

- Every `state=paused` field present in both bash and Python output (pause feature parity).
- `ralph-status` and `ralph-status-watch` render Python-written status JSON identically to bash-written.
- Process cleanup verified: no leftover `claude-code`, `python`, or `uv` processes after `/ralph-stop`.
- Heartbeat freshness preserved across language boundary (a bash-launched run resumed via Python doesn't get false "crashed" verdicts).

### Feature label
`feature:ralph-python-refactor` (or shorter `feature:py-refactor`). The slug is mechanical for `/ralph-review name=ralph-python-refactor` later.

### Historical-context appendix (PRD must mirror; port tasks must NOT reference)

The "Appendix: Historical context" section above is the curated list of historical tasks that document load-bearing invariants. The PRD generated from this distillation MUST copy that appendix verbatim into its own "Reference" section so it's discoverable for any port task that hits ambiguity. Individual port tasks MUST NOT enumerate these task IDs in their `-d` per R16 spirit — the port-task spec is the bash source line range, not a history lesson. Old-task lookup is an on-demand escape valve (`git blame` + `backlog task view`), not primary input.
