---
export: true
title: Embed `refine` into the Ralph plugin as `ralph-refine`
type: design
---

# Embed `refine` into the Ralph plugin as `ralph-refine`

Rewrite the standalone `refine` adversarial author↔reviewer refinement loop
(`~/dev/ai/refine`, bash `refine.sh`) as a Python-based, separately-invocable
`ralph-refine` skill inside this repo (the Ralph Claude Code plugin
marketplace), reusing the plugin's existing tool / devcontainer / signal layer.

## Architecture decision

**Consolidate & retire.** Port `refine.sh` to Python as a first-class
`ralph-refine` skill in the `ralph` plugin, then retire the standalone
`~/dev/ai/refine` repo (separate follow-up, in that repo). One repo, one
upgrade path, one test suite — no more "upgrade Ralph infrastructure" chores in
a second codebase.

The refine loop is Ralph's non-code sibling: Ralph loops an autonomous *coder*
over backlog tasks until Done; refine loops an *author↔reviewer* over a digital
artifact (markdown article, draw.io, PlantUML) until a quality score threshold.
The two share infra DNA (identical CLI vocabulary, LLM-invocation shape,
devcontainer/on-error/retry semantics), so the port sits on top of the
already-tested Python tool layer rather than re-implementing it.

**Module layout — sub-package reusing `ralph`.** New `ralph/refine/`
sub-package imports `ralph.tools`, `ralph.devcontainer`, `ralph.signals`
directly. Refine-specific modules only: `loop` (threshold loop), `roles`
(prompt composition), `extract` (`<artifact>`/`<summary>`/`SCORE:` parsing),
`summary` (score/delta table), `args`, `cli`. Not reused: `loop.py` (backlog /
one-task-STOP coupled), `prompts.py`, `status`/`heartbeat` (phase-2 only).

**Skill scope — Option A.** `ralph-refine` is a separately-invocable skill with
its own `SKILL.md` + `examples/` + launcher shim(s). Its **Python code lives in
the shared tree** as `ralph/refine/` under `ralph-run/scripts/`, because the
entire Python toolchain (`pytest.pythonpath`, `ruff.src`, `pyright.include`) is
pinned to that single root and `ralph.refine` must import `ralph.tools` from the
same package tree. This keeps the embed small (zero toolchain churn) while the
skill stays first-class and separately invocable.

**Execution model — both, phased.** Foreground CLI core first (matches how
refine is used today: short 3–5 iteration runs, look at the artifact when
done). Detached/watch wrapper is a deferred phase-2 layer that *wraps* the
unchanged core.

**Backlog-independent.** Roles + prompt/draft are plain files; output goes to
`iterations/`. Refine is a self-contained utility that happens to ship in the
plugin and works in any repo (even non-Ralph ones). No coupling to
`backlog`/`tasks.py`.

## Components / flows

- **Entrypoint:** repo-root `refine.sh` mirrors `ralph.sh` exactly — same
  5-tier resolver, but resolves `refine_orchestrator.py` and execs `uv run`.
  New R11 template pair (`templates/root/refine.sh` ↔ repo-root `refine.sh`);
  `ralph-init` seeds it unconditionally alongside `ralph.sh`.
- **`refine_orchestrator.py`:** thin PEP-723 entrypoint mirroring
  `ralph_orchestrator.py` (inserts its dir into `sys.path`, dispatches into
  `ralph.refine.cli:main`).
- **Loop data flow, per iteration N:**
  1. *Author* — `roles` composes: iter 1 = author role + (task | draft);
     iter > 1 = author role + prev artifact + prev *full* review; append
     "wrap output in `<artifact>…</artifact>`". `ClaudeTool.run(prompt,
     timeout)` (reused, incl. devcontainer prefix) → read `result.stdout_path`
     → `extract.artifact()` → save `iterations/artifact-vN.{type}`.
  2. *Reviewer* — role + current artifact + (prev `<summary>` if N > 1) +
     "emit `SCORE: N` and `<summary>…</summary>`". `tool.run()` → read tee →
     `extract.score()` + `extract.summary()` → save `iterations/review-vN.md`
     → return score.
  3. *Threshold* — score ≥ threshold → copy `final.{type}`, write `summary.md`,
     exit 0. Max-iterations → warn, copy last as `final`, write `summary.md`,
     exit 1.
- **Reused verbatim:** claude/opencode tool factory, `_subprocess.execute`
  (timeout=124, tee, process-group kill), `devcontainer.py`, `signals.py`
  (`on_spawn` SIGTERM forwarding).
- **Ported to Python (small):** `--on-error stop|continue|retry` +
  `--retry-count`; `--resume` (scan output-dir for last complete
  artifact+review pair, re-parse scores); `--dry-run`; `--verbose`.
- **Example roles:** ported verbatim from `~/dev/ai/refine/examples/` into
  `skills/ralph-refine/examples/{article,drawio,plantuml}/{author,reviewer,prompt}.md`.
  They already encode the `<artifact>`/`SCORE:`/`<summary>` protocol; drawio
  role leans on the `arch-draw` skill.
- **Tests:** the 15 bats cases become pytest under `ralph-run/tests/`
  (`test_refine_args/extract/roles/loop/e2e.py`), incl. a fake-claude e2e stub;
  reused tool layer needs no new tests.

## Scope cuts

- **No literal bash port.** Rewrite on shared Python infra, not a 1:1 re-type
  of 871 bash lines.
- **`loop.py` not reused** — different loop contract (stateful within a run,
  score-terminated, no backlog). Refine gets its own smaller loop.
- **Phase-2 detach deferred** — `.refine-status.json` + heartbeat + watch skill
  + launcher shim are a later additive layer; MVP is foreground only.
- **Combined-stdout tee accepted** — `execute()` tees stdout+stderr together;
  extraction keys on `<artifact>` tags and a line-anchored `^SCORE:`, so stderr
  outside the block is ignored. A separate-streams tool variant is only added
  if it ever bites (it doesn't with `claude --print` in practice).
- **Common-package extraction deferred** — `ralph.tools`/`devcontainer`/
  `signals` stay under `ralph-run/scripts/` for now.
- **Retiring `~/dev/ai/refine` is out of scope for this feature** — happens in
  that repo (archive or thin-consumer conversion) via a separate `ralph-handoff`
  task after the embed ships.

## Open questions

- **Common-package extraction (deferred, not blocking):** later refactor lifts
  `ralph.tools`/`devcontainer`/`signals` into a plugin-level shared package that
  both `ralph.loop` and `ralph.refine.loop` import. Option A makes this a
  mechanical, symmetric, test-covered move — filed as future work, not part of
  this feature.
- **Phase-2 detach shape:** exact `.refine-status.json` schema (score-per-
  iteration vs task-per-iteration) and whether the watch skill is a new
  `ralph-refine-watch` or a parametrized reuse of `ralph-status-watch` —
  decided when phase 2 is scoped.

Resolved during brainstorm: end goal (consolidate & retire), exec model (both,
foreground first), backlog independence (independent), module layout
(sub-package reusing `ralph`), skill scope (Option A), entrypoint (root
`refine.sh` + R11 + unconditional init-seeding).

## Hand-off

Next: `ralph-prd` to formalize as PRD (this is PRD-shaped — multiple cross-task
invariants: the tool-layer reuse contract, the `<artifact>`/`SCORE:`/`<summary>`
tag protocol, R11 template parity, exec-model phasing), then `ralph-backlog` to
generate tasks.

## Distilled for ralph-task

**Direction:** Consolidate & retire — port standalone `refine.sh` to Python as a
first-class, separately-invocable `ralph-refine` skill in the `ralph` plugin,
reusing the plugin's tool/devcontainer/signal layer; foreground CLI first,
detach deferred; backlog-independent.

**Locked decisions (with rationale):**
- **Module layout = sub-package `ralph/refine/` under `ralph-run/scripts/`.**
  *Rationale:* the Python toolchain (pytest/ruff/pyright) is pinned to that
  single root and `ralph.refine` must import `ralph.tools` from the same tree —
  zero toolchain churn.
- **Skill scope = Option A** (skill owns `SKILL.md` + `examples/` + shims;
  Python shared). *Rationale:* keeps `ralph-refine` first-class and separately
  invocable without duplicating the Python root or adding cross-dir imports.
- **Entrypoint = root `refine.sh` mirroring `ralph.sh`** (5-tier resolver →
  `refine_orchestrator.py`), R11 template pair, seeded unconditionally by
  `ralph-init`. *Rationale:* "works wherever the plugin is installed" for free;
  consistency with `ralph.sh`.
- **Reuse `ClaudeTool`/`execute` as-is** (combined-stdout tee). *Rationale:*
  extraction keys on tags + line-anchored `^SCORE:`; separate streams not needed
  for MVP.
- **Backlog-independent, file-driven.** *Rationale:* keeps refine usable in any
  repo; matches its existing PRD.
- **Foreground first, detach deferred.** *Rationale:* matches current usage;
  core stays unchanged when detach wraps it later.
- **Single-approval invocation (mirrors `ralph-run`).** When Claude launches
  refine on the user's behalf, exactly one permission prompt fires — the
  sandbox-bypass launch of `refine.sh`; every other command runs without
  prompting (read-only sandbox-safe checks, or helper shims invoked as
  `bash <abs-path>` matched by seeded `Bash(bash <abs-path>:*)` allow rules).
  *Rationale:* the user's standing UX requirement — approve only the launch.

**Scope cuts:**
- No literal bash port; no reuse of `loop.py`/`prompts.py`.
- Phase-2 detach (`.refine-status.json`, heartbeat, watch skill, launcher shim)
  deferred.
- Common-package extraction deferred.
- Retiring `~/dev/ai/refine` is a separate follow-up in that repo.

**Acceptance criteria (sketch):**
- `ralph/refine/` sub-package exists with `args`, `roles`, `extract`, `loop`,
  `summary`, `cli`; imports `ralph.tools`/`devcontainer`/`signals`.
- `refine_orchestrator.py` + repo-root `refine.sh` (5-tier resolver) run a full
  loop; `templates/root/refine.sh` R11 pair matches byte-for-byte; `ralph-init`
  seeds it.
- CLI parity with `refine.sh`: `--prompt`/`--draft` (mutually exclusive),
  `--author`/`--reviewer` (required), `--type md|drawio|puml`, `--tool`,
  `--model`, `--effort`, `--timeout`, `--max-iterations`, `--threshold`,
  `--output-dir`, `--on-error`, `--retry-count`, `--devcontainer`, `--resume`,
  `--verbose`, `--dry-run`.
- Author/reviewer/threshold loop produces `iterations/artifact-vN.{type}`,
  `review-vN.md`, `final.{type}`, `summary.md`; exit 0 at threshold, 1 at max.
- `extract` handles single-line tags, leading-blank stripping, missing-tag
  stdout dump, valid/invalid `SCORE:`.
- 3 example role sets ported verbatim under `skills/ralph-refine/examples/`.
- `skills/ralph-refine/SKILL.md` documents invocation; skill is separately
  invocable.
- `uv run pytest` green (new `test_refine_*` incl. fake-claude e2e),
  `uv run ruff check .` clean, pyright strict on `ralph/refine/`.
- Single-approval property: the `ralph-refine` launch flow fires exactly one
  permission prompt (the sandbox-bypass launch); any helper shim is seeded as a
  narrow `Bash(bash <abs-path>:*)` allow rule in the R11-paired settings
  template — never a second prompt.

**Implementation checklist:**
- Scaffold `ralph/refine/` package + `refine_orchestrator.py`.
- Port `args` (parse + validate) with pytest.
- Port `extract` (artifact/summary/score) with pytest (incl. TASK-10/12/16
  cases).
- Port `roles` (prompt composition) with pytest.
- Port `loop` (author→reviewer→threshold, on-error/retry, resume, summary)
  reusing tool/devcontainer/signals; pytest.
- Add repo-root `refine.sh` + `templates/root/refine.sh` (R11); wire
  `ralph-init` seeding.
- Port 3 example role sets verbatim into `skills/ralph-refine/examples/`.
- Write `skills/ralph-refine/SKILL.md` (documents the single sandbox-bypass
  launch; helpers, if any, use the `bash <abs-path>` seeded-allow-rule pattern).
- Seed any refine helper-shim allow rule into the settings templates (R11).
- Add fake-claude e2e test; ensure pytest/ruff/pyright green.
- (Follow-up, separate) `ralph-handoff` task to retire `~/dev/ai/refine`.
