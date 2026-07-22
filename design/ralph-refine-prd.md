# PRD: ralph-refine — Embed the Adversarial Refinement Loop into the Ralph Plugin

## Introduction

`refine` is a standalone bash tool (`~/dev/ai/refine/refine.sh`) that iteratively
improves a *digital artifact* — a markdown article, draw.io diagram, or PlantUML
diagram — through two LLM roles: an **author** that generates/revises the
artifact and a **reviewer** that scores it (1–10) and gives feedback. The loop
repeats until a quality threshold or a max-iteration cap.

This feature rewrites `refine` in Python as a **separately-invocable
`ralph-refine` skill** inside this repo (the Ralph Claude Code plugin
marketplace), reusing the plugin's already-tested tool / devcontainer / signal
layer. It is Ralph's non-code sibling loop: Ralph loops an autonomous *coder*
over backlog tasks; `ralph-refine` loops an *author↔reviewer* over an artifact.
Consolidating it into the plugin removes a second repo to maintain and gives it
one install/upgrade path and one test suite.

Full design rationale and locked decisions: `design/ralph-refine-brainstorm.md`.

## Goals

- Ship a Python `ralph/refine/` sub-package that reuses `ralph.tools`,
  `ralph.devcontainer`, and `ralph.signals` (no re-implementation of subprocess/
  timeout/devcontainer logic).
- Preserve full CLI and behavioral parity with `refine.sh` (foreground mode).
- Ship `ralph-refine` as a first-class, separately-invocable skill with its own
  `SKILL.md`, example roles, and root shim.
- Match the repo quality bar: `uv run pytest` green, `uv run ruff check .`
  clean, `pyright` strict on the new package.
- Keep `refine` backlog-independent and runnable in any repo.

## User Stories

### US-001: refine Python sub-package scaffold + entrypoint
**Description:** As a developer, I need a `ralph/refine/` package and a
`refine_orchestrator.py` entrypoint so the refine loop runs as Python under the
shared toolchain.

**Acceptance Criteria:**
- [ ] `plugins/ralph/skills/ralph-run/scripts/ralph/refine/__init__.py` exists
      and the package imports `ralph.tools`, `ralph.devcontainer`,
      `ralph.signals` without error
- [ ] `plugins/ralph/skills/ralph-run/scripts/refine_orchestrator.py` exists,
      mirrors `ralph_orchestrator.py` (PEP-723 header, inserts its dir into
      `sys.path`), and dispatches into `ralph.refine.cli:main`
- [ ] `refine_orchestrator.py --help` prints usage and exits 0
- [ ] `pyright` strict passes on `ralph/refine/`
- [ ] `uv run ruff check .` passes

### US-002: CLI argument parsing and validation
**Description:** As a user, I want `refine` to accept the same flags as
`refine.sh` and reject invalid combinations, so existing invocations keep working.

**Acceptance Criteria:**
- [ ] Parses: `--prompt`, `--draft`, `--author`, `--reviewer`, `--type`,
      `--tool`, `--model`, `--effort`, `--timeout`, `--max-iterations`,
      `--threshold`, `--output-dir`, `--on-error`, `--retry-count`,
      `--devcontainer`, `--resume`, `--verbose`, `--dry-run`
- [ ] Defaults match `refine.sh` (`type=md`, `tool=claude`,
      `model=claude-opus-4-8`, `effort=medium`, `timeout=15`,
      `max-iterations=10`, `threshold=8`, `output-dir=iterations/`,
      `on-error=stop`, `retry-count=2`)
- [ ] `--prompt` and `--draft` are mutually exclusive; exactly one is required
      (violation → error message + exit 1)
- [ ] `--author` and `--reviewer` are required; a missing file → error + exit 1
- [ ] `--type` accepts only `md|drawio|puml`; `--effort` only
      `low|medium|high|max`; `--on-error` only `stop|continue|retry`;
      `--threshold` 1–10; `--timeout`/`--max-iterations` ≥ 1;
      `--retry-count` ≥ 0 — each invalid value → error + exit 1
- [ ] pytest covers each validation branch (`test_refine_args.py`)
- [ ] `uv run pytest` and `uv run ruff check .` pass

### US-003: Artifact / summary / score extraction
**Description:** As the loop, I need to extract the author's artifact and the
reviewer's score and summary from LLM output, so iterations chain correctly.

**Acceptance Criteria:**
- [ ] `extract.artifact()` returns the content between `<artifact>` and
      `</artifact>`; missing tags → error signalled to caller
- [ ] `extract.summary()` returns the content between `<summary>` and
      `</summary>`; missing tags → error signalled to caller
- [ ] `extract.score()` parses a line-anchored `^SCORE:\s*N`, validating N is an
      integer 1–10; missing or out-of-range → error signalled to caller
- [ ] Single-line tags (open+content+close on one line) are handled (parity with
      refine TASK-10)
- [ ] Leading blank lines inside tags are stripped (parity with refine TASK-12)
- [ ] On extraction failure the tee'd LLM stdout is surfaced for post-mortem
      (parity with refine TASK-16)
- [ ] Extraction reads from a `ToolResult.stdout_path` tee file (combined
      stdout+stderr) and ignores noise outside the tag block
- [ ] pytest covers all above cases (`test_refine_extract.py`)

### US-004: Prompt composition (author & reviewer roles)
**Description:** As the loop, I need to compose author and reviewer prompts from
role files plus prior context, so each LLM call has the right inputs.

**Acceptance Criteria:**
- [ ] Author iter 1 with `--prompt`: role text + task prompt
- [ ] Author iter 1 with `--draft`: role text + draft content
- [ ] Author iter > 1: role text + previous artifact + previous *full* review
- [ ] Author prompt appends the "wrap output in `<artifact>…</artifact>`"
      instruction
- [ ] Reviewer prompt: role text + current artifact + (previous `<summary>` when
      iteration > 1)
- [ ] Reviewer prompt appends the "emit `SCORE: N` and `<summary>…</summary>`"
      instruction
- [ ] pytest covers each composition path (`test_refine_roles.py`)

### US-005: Refinement loop, output structure, and summary
**Description:** As a user, I want the loop to run author→reviewer per iteration,
stop at threshold or max, and save every version, so I can inspect progress and
get a final artifact.

**Acceptance Criteria:**
- [ ] Per iteration: run author → save `{output-dir}/artifact-vN.{type}`; run
      reviewer → save `{output-dir}/review-vN.md`; print iteration number + score
- [ ] Author/reviewer LLM calls go through the reused claude/opencode tool
      factory (`tool.run(prompt, timeout_sec)`), honoring `--devcontainer`,
      `--model`, `--effort`, `--timeout`
- [ ] Loop stops when score ≥ `--threshold`: copies `{output-dir}/final.{type}`,
      writes `{output-dir}/summary.md`, exits 0
- [ ] Loop stops at `--max-iterations`: warns, copies last artifact to
      `final.{type}`, writes `summary.md`, exits 1
- [ ] `summary.md` contains an iteration table (iteration, score, delta) plus
      final score / threshold / iteration count
- [ ] `--on-error stop|continue|retry` (+ `--retry-count`) governs LLM-call
      failures (timeout exit code 124 or nonzero exit)
- [ ] `--resume` detects the last complete `artifact-vN`+`review-vN` pair,
      re-parses prior scores, and continues (or reports nothing-to-do when
      threshold already met or all iterations complete)
- [ ] `--dry-run` prints the iteration-1 prompts without any LLM call and exits 0
- [ ] `--verbose` prints composed prompts before each call
- [ ] SIGTERM/SIGINT during an LLM call cleans up the child process group (reused
      `signals.py` `on_spawn`)
- [ ] pytest covers threshold stop, max-iter stop, exit codes, on-error
      strategies, resume, and summary/delta (`test_refine_loop.py`)

### US-006: Root `refine.sh` shim + R11 template parity + init seeding
**Description:** As a user, I want a `refine.sh` at my project root that finds the
installed plugin's orchestrator, so refine runs wherever the plugin lives.

**Acceptance Criteria:**
- [ ] Repo-root `refine.sh` mirrors `ralph.sh`'s 5-tier resolver but resolves
      `refine_orchestrator.py` and execs `uv run`
- [ ] `plugins/ralph/skills/ralph-init/templates/root/refine.sh` exists and is
      byte-identical to the repo-root `refine.sh` (new R11 pair)
- [ ] `ralph-init` seeds `refine.sh` into a project root unconditionally,
      alongside `ralph.sh`
- [ ] `.claude/task-reviewer-rules.md` R11 table lists the new
      `refine.sh` ↔ `templates/root/refine.sh` pair
- [ ] `bash -n refine.sh` and `bash -n templates/root/refine.sh` pass; shim
      satisfies R5 portability
- [ ] Running `./refine.sh --help` from the repo root prints usage (resolves the
      in-repo orchestrator via tier 2)

### US-007: Example roles ported verbatim
**Description:** As a user, I want ready-made author/reviewer role sets for the
three artifact types, so I can run refine out of the box.

**Acceptance Criteria:**
- [ ] `skills/ralph-refine/examples/article/{author,reviewer,prompt}.md` present
- [ ] `skills/ralph-refine/examples/drawio/{author,reviewer,prompt}.md` present
      (drawio reviewer references the `arch-draw` skill)
- [ ] `skills/ralph-refine/examples/plantuml/{author,reviewer,prompt}.md` present
- [ ] Each reviewer role contains the `SCORE: N` (1–10) output instruction and
      the `<summary>` protocol; each author role documents the `<artifact>`
      protocol
- [ ] Content matches the source `~/dev/ai/refine/examples/` sets

### US-008: ralph-refine SKILL.md
**Description:** As a Claude Code user, I want a `ralph-refine` skill so I can
discover and invoke refine and understand how to run it.

**Acceptance Criteria:**
- [ ] `plugins/ralph/skills/ralph-refine/SKILL.md` exists with a description that
      makes the skill separately invocable/discoverable
- [ ] Documents invocation: `./refine.sh --prompt … --author … --reviewer …`,
      the `--draft` mode, `--type`, `--threshold`, and where output lands
      (`iterations/`)
- [ ] References the bundled example role sets
- [ ] No `plugin.json` edit required (skills auto-discover) — verified the skill
      is listed by the plugin loader
- [ ] **Single-approval flow:** when the skill launches refine on the user's
      behalf, exactly one permission prompt fires (the sandbox-bypass `refine.sh`
      launch); the SKILL.md documents this and issues the launch as a single
      sandbox-bypass Bash call
- [ ] Any helper command the SKILL.md runs is either a read-only sandbox-safe
      check or a `bash <abs-path>` shim covered by a seeded
      `Bash(bash <abs-path>:*)` allow rule (R11-paired settings template) — no
      second prompt

### US-009: End-to-end test + green toolchain
**Description:** As a maintainer, I want an e2e test with a fake LLM and a fully
green toolchain, so the port is proven without a real LLM call.

**Acceptance Criteria:**
- [ ] `test_refine_e2e.py` uses a fake-claude stub (author emits `<artifact>`,
      reviewer emits `SCORE:` + `<summary>`) and asserts the loop converges,
      writes `final.{type}` + `summary.md`, and returns exit 0 at threshold
- [ ] The reused tool/subprocess/devcontainer/signal layer gets **no** new tests
      (already covered)
- [ ] `uv run pytest` passes with the new `test_refine_*` tests added
- [ ] `uv run ruff check .` passes
- [ ] `pyright` strict passes on `ralph/refine/`

## Functional Requirements

- FR-1: `ralph/refine/` MUST live under `plugins/ralph/skills/ralph-run/scripts/`
  (the single Python root pinned by `pytest.pythonpath`/`ruff.src`/
  `pyright.include`) and import the shared `ralph.*` modules directly.
- FR-2: The refine loop MUST invoke LLMs only through the existing
  `ralph.tools` factory (claude/opencode) — no bespoke subprocess/timeout code.
- FR-3: Author output protocol = content wrapped in `<artifact>…</artifact>`;
  reviewer output protocol = a `SCORE: N` line (1–10) plus a
  `<summary>…</summary>` block. Extraction MUST be resilient to combined
  stdout+stderr noise outside the tag block.
- FR-4: The loop MUST terminate on `score ≥ threshold` (exit 0) or
  `iterations ≥ max-iterations` (exit 1), and always write `final.{type}` and
  `summary.md`.
- FR-5: CLI flags, defaults, and validation MUST match `refine.sh` (foreground).
- FR-6: `refine.sh` MUST resolve `refine_orchestrator.py` via the same 5-tier
  precedence as `ralph.sh` and MUST be R11-paired with a template; `ralph-init`
  MUST seed it.
- FR-7: `ralph-refine` MUST be a separately-invocable skill with its own
  `SKILL.md` and bundled example roles; it MUST NOT couple to `backlog`/
  `tasks.py`.
- FR-8: **Single-approval invocation.** When `ralph-refine` launches refine on
  the user's behalf, exactly ONE permission prompt MUST fire — the sandbox-bypass
  launch of `refine.sh`. Every other command MUST run without prompting:
  read-only checks stay sandbox-safe, and any helper shim MUST be invoked as
  `bash <abs-path>` with a matching `Bash(bash <abs-path>:*)` allow rule seeded
  by `ralph-init` into the settings templates (R11-paired). Mirrors the
  `ralph-run` launch UX.

## Non-Goals

- **Detached / watch execution (phase 2).** No `.refine-status.json`, heartbeat,
  `ralph-refine-watch`, or launcher shim in this feature — the foreground core
  is designed so a later layer can wrap it unchanged.
- **Common-package extraction.** `ralph.tools`/`devcontainer`/`signals` stay
  under `ralph-run/scripts/`; lifting them into a plugin-level shared package is
  deferred future work.
- **Retiring `~/dev/ai/refine`.** Archiving or converting the standalone repo to
  a thin consumer happens in that repo via a separate `ralph-handoff` task after
  this ships.
- **Backlog integration.** Refine stays file-driven and backlog-independent.
- **Separate-streams tool variant.** Not needed for MVP; combined-stdout tee is
  accepted.
- **New artifact types.** Only `md`, `drawio`, `puml` (parity with `refine.sh`).

## Technical Considerations

- **Cross-task invariants** the reviewer must hold across all stories:
  1. *Tool-layer reuse contract* — all LLM I/O flows through `ralph.tools`;
     `ToolResult.stdout_path` is the tee file the extractor reads.
  2. *Tag protocol* — `<artifact>` / `^SCORE: N` / `<summary>` is the single
     contract shared by `roles.py`, `extract.py`, the example roles, and the
     e2e stub.
  3. *R11 template parity* — root `refine.sh` and its template stay
     byte-identical; the R11 table is updated.
  4. *Exec-model phasing* — the loop core emits a per-iteration score event so a
     future detach layer can observe it without touching the core.
  5. *Single-approval invocation* — the ralph-refine launch flow prompts exactly
     once (the sandbox-bypass launch); helper shims are pre-authorized via seeded
     `Bash(bash <abs-path>:*)` allow rules, never adding a second prompt (parity
     with `ralph-run`).
- Reuse targets: `ralph.tools` (claude/opencode + `_subprocess.execute`,
  timeout=124, tee, process-group kill), `ralph.devcontainer`, `ralph.signals`.
- Not reusable: `ralph.loop` (backlog/one-task-STOP coupled), `ralph.prompts`,
  `ralph.status`/`ralph.heartbeat` (phase-2 only).
- Ordering: US-001 → US-002/003/004 (independent units) → US-005 (loop, depends
  on 002/003/004) → US-006/007/008 (packaging, depend on 001/005) → US-009
  (e2e + green bar, depends on all).

## Success Metrics

- `./refine.sh --prompt examples/article/prompt.md --author … --reviewer …`
  converges and writes `iterations/final.md` (parity with the old `make demo`).
- `uv run pytest` count increases by the new `test_refine_*` suite; all green.
- Zero changes required to `ralph.tools`/`devcontainer`/`signals` source.
- `ralph-refine` appears as an invocable skill after plugin reload.

## Open Questions

None blocking. Deferred to future work (see brainstorm): common-package
extraction, and the exact phase-2 detach schema / watch-skill shape.
