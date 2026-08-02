---
export: true
id: doc-1
title: >-
  Ralph Loop Comparative Research - Huntley canonical, Umputun ralphex, Claude
  Code goal command, this project
type: specification
created_date: '2026-06-21 07:01'
---

# Ralph Loop Comparative Research

Comparison + recommendations report covering four approaches to autonomous AI coding loops:

1. **Canonical Ralph** — Geoffrey Huntley, `ghuntley.com/ralph/` (mid-2025)
2. **ralphex** — Umputun, `github.com/umputun/ralphex` (Jan 2026, Go)
3. **`/goal` command** — Anthropic, Claude Code v2.1.139 (May 2026)
4. **This project** — Ralph + Backlog.md (fork; this repo)

---

## 0. Executive Summary

The four approaches occupy distinct points on the same design axis: **how much structure do you put around a `while-true` agent invocation?**

- **Huntley (canonical):** ~5 lines of bash, no structure. The loop is the moat; specs and git carry state. Cheap, fast, philosophically pure; weak guardrails, low reproducibility.
- **`/goal`:** Single-session, single-condition, evaluator-driven. Built-in, zero setup. Not a task system — it's a stop-condition wrapper around the existing chat session.
- **ralphex:** ~10k lines of Go. Plan-file task model with `### Task N:` + checkboxes, sentinel signal taxonomy, multi-phase review pipeline (Claude → external codex → Claude), pluggable executors, worktree isolation, web dashboard. The maximalist Ralph fork.
- **This project:** Bash orchestrator (~900 lines) + Claude Code skills + backlog.md CLI integration. Per-task branches, mandatory `task-reviewer` agent, heartbeat/status JSON, `ScheduleWakeup`-driven watch chain, usage-cap pause, brainstorm→PRD→backlog distillation pipeline. **The most Claude-Code-native of the four.**

**Key recommendation:** This project has good bones and several things ralphex lacks (heartbeat liveness, structured status JSON, usage-cap pause, `ScheduleWakeup` chain, brainstorm distillation contract). The biggest opportunities to borrow are: (a) **richer signal taxonomy** beyond `<promise>COMPLETE</promise>`, (b) **external reviewer pass** with a different model in the review loop, (c) **stalemate detection** for review iteration, (d) **worktree isolation per task** to remove the volume-overlay drift class of bug, and (e) **pattern-based retry classification** to distinguish rate-limits from transient 5xx from fatal. See §6.

---

## 1. Canonical Ralph (Geoffrey Huntley)

> **Verification status (2026-06-21):** §1.1–1.6 below were re-checked against the canonical post `https://ghuntley.com/ralph/` via WebFetch. Direct quotes are now verbatim from the fetched source. Companion posts (`/specs/`, etc.) are partially paywalled — visible excerpts are cited where used, and claims that depend on paywalled content are removed rather than paraphrased. Several items from the first draft of this section (containerization, `--dangerously-skip-permissions`, Claude Max $200/mo + "overnight" cost framing) were NOT found in the canonical /ralph/ post and have been removed. See §1.7 for what was removed and why.

### 1.1 Origin & motivation

The canonical post is **"Ralph Wiggum as a 'software engineer'"** by Geoffrey Huntley, published **14 Jul 2025**, at `https://ghuntley.com/ralph/`. The name is a Simpsons reference — Ralph as a sweet but slow-witted engineer.

Huntley's stated framing (verbatim):

> *"That's the beauty of Ralph — the technique is deterministically bad in an undeterministic world."*

> *"Ralph can replace the majority of outsourcing at most companies for greenfield projects."*

> *"Ralph is very good at making playgrounds, but he comes home bruised because he fell off the slide, so one then tunes Ralph by adding a sign next to the slide saying 'SLIDE DOWN, DON'T JUMP, LOOK AROUND,' and Ralph is more likely to look and see the sign."*

The motivation is not "context rot" or "stalled judgment" (those are common community framings but not in this post). The actual argument is **economic**: at the end of the post Huntley quotes a contract MVP delivery at $297 actual cost versus a $50,000 USD contract price — i.e., the loop is a labor-arbitrage / margin argument, not an architecture argument.

### 1.2 Loop mechanics

The canonical shape, verbatim from the post:

```bash
while :; do cat PROMPT.md | claude-code ; done
```

That is the entire loop. No `npx`, no `--print`, no `--dangerously-skip-permissions`, no `--output-format stream-json`. The inner tool is `claude-code`; codex/opencode/etc. are NOT mentioned in this post as alternates.

- **Outer:** `bash` `while :`. No iteration cap, no built-in stop signal. Termination is manual.
- **Inner:** standard `claude-code` invocation reading `PROMPT.md` on stdin.
- **State between iterations:** lives on disk in the files §1.3 enumerates plus the git working tree.
- **Stop signal:** none mentioned in the post. "We're done" sentinel strings are downstream community convention, not part of the canonical loop.

### 1.3 Task source

The post names five files (verbatim names quoted from the fetched content):

- **`PROMPT.md`** — the core loop input; the same file is `cat`'d every iteration.
- **`@fix_plan.md`** — *"prioritized todo list"*.
- **`@AGENT.md`** — *"compilation and execution instructions"*. Note: singular `AGENT.md`, not the more common community spelling `AGENTS.md`.
- **`specs/*`** — *"compiler specifications"* (the post is about a programming-language compiler project).
- **`@specs/stdlib/*`** — *"standard library specifications"*.

The agent reads and rewrites these — markdown only, no schema, no JSON. The `@` prefix is the post's notation for "file the agent references"; the actual filenames in the worktree are without `@`.

Ryan Carson's parallel variant (`prd.json` + `jq` + `progress.txt`) is cited in this project's README as a predecessor; the two lineages converged on the same loop shape independently.

### 1.4 Guardrails (what IS in the post)

What the post explicitly recommends:

- **Aggressive git workflow** (verbatim): *"When the tests pass update the @fix_plan.md, then add changed code and @fix_plan.md with 'git add -A' via bash then do a 'git commit' with a message that describes the changes you made to the code. After the commit do a 'git push' to push the changes to the remote repository."*
- **Semver tagging** (verbatim): *"As soon as there are no build or test errors create a git tag. If there are no git tags start at 0.0.0 and increment patch by 1 for example 0.0.1 if 0.0.0 does not exist."*

What's notably **absent** from the post: no per-task branching, no reviewer agent, no hooks, no pre-commit gates, no mention of containers/devcontainers/VMs, no `--dangerously-skip-permissions`, no sandboxing discussion. The agent runs on the working branch and commits + pushes directly.

### 1.5 Cost / usage management

The post does **not** mention Claude Max, the $200/month subscription, the 5-hour Anthropic usage block, `ccusage`, block-boundary detection, or "running overnight." Those were paraphrased into the first draft of this section but are not present in the canonical /ralph/ post.

What IS in the post is a single direct economic comparison (verbatim):

> *"Cost of a $50k USD contract, delivered, MVP, tested + reviewed with @ampcode. $297 USD."*

That is the only cost framing the canonical post offers — actual project economics rather than meta-discussion of cost ceilings or per-token rate limits.

### 1.6 Acknowledged failure modes (verbatim)

Real quotes from the post — these are the failure modes Huntley himself names, not paraphrases:

- *"Ralph will test you. Every time Ralph has taken a wrong direction in making CURSED, I haven't blamed the tools; instead, I've looked inside."* — i.e., when the loop misbehaves, the problem is upstream in prompts/specs, not the loop itself.
- *"you'll wake up to a broken codebase that doesn't compile from time to time"* — broken-state-on-resume is a known and accepted outcome.
- *"Claude has the inherent bias to do minimal and placeholder implementations"* — model bias that bleeds through.
- *"Ralph has three states. Under baked, baked, or baked with unspecified latent behaviours (which are sometimes quite nice!)"* — explicit acknowledgment that output is non-deterministic and may contain emergent behavior.

Editorial commentary (NOT a Huntley quote; my analytic framing for this report): once you add stop conditions, retries, error classification, cost caps, and a review step, you've reinvented an agent framework in bash. This project's ~900-line `ralph.sh` is empirical confirmation of that observation, but Huntley himself does not concede the point in /ralph/.

### 1.7 What was removed from the first draft and why

For provenance integrity, calling these out explicitly. Each item below was in the original §1 paraphrased from training-data recall; WebFetch against the canonical /ralph/ post (and the visible excerpt of /specs/) did NOT confirm them.

| Removed claim | Where the original draft put it | Status after WebFetch |
|---|---|---|
| `npx --yes @anthropic-ai/claude-code -p --dangerously-skip-permissions` as canonical inner invocation | §1.2 | NOT in /ralph/. The post shows `claude-code` only. |
| "Codex CLI is the documented alternate" | §1.2 | NOT in /ralph/. Codex is not mentioned. |
| Containerization / devcontainer / VM / "disposable environment" / "make blast radius cheap" | §1.4 | NOT in /ralph/. NOT in the visible /specs/ excerpt. May exist in paywalled material or other posts — cannot verify, so removed. |
| `--dangerously-skip-permissions` as Huntley-endorsed | §1.4 | NOT in /ralph/. NOT in /specs/ excerpt. Removed. |
| Claude Max $200/mo + "buy the subscription, run overnight, don't meter" | §1.5 | NOT in /ralph/. NOT in /specs/ excerpt. Cost framing in the post is per-project economics ($297 vs $50k), not subscription-tier advice. |
| "5-hour usage blocks as the relevant ceiling" | §1.5 | NOT in /ralph/. Removed. |
| "Spec quality is the bottleneck — vague specs → endless mediocre code" | §1.6 | The actual quote is *"Ralph will test you... I've looked inside"* — different framing, same general territory. Replaced with the verbatim quote. |
| "Drift without a reviewer — agent deletes/weakens tests to make them pass" | §1.6 | NOT in /ralph/ as a Huntley claim. Removed from §1; the underlying concern is still load-bearing for §6.2 (cross-model reviewer recommendation), which now stands on its own merit. |
| "Context window exhaustion mid-turn → half-finished commits" | §1.6 | NOT in /ralph/. Removed. The "broken codebase that doesn't compile" quote covers similar territory differently. |
| "Reproducibility is poor — Huntley frames as feature ('evolution')" | §1.6 | NOT in /ralph/. The "three states" quote is the actual acknowledgment. Replaced. |

Provenance note for §6 (Recommendations): the recommendation in §6.2 (external-reviewer pass with a different model) was originally motivated by a removed paraphrase. Re-reading the canonical post does not invalidate the recommendation — Huntley's own *"you'll wake up to a broken codebase"* is sufficient motivation for a cross-model review pass. §6.2 stands.

---

## 2. ralphex (Umputun)

### 2.1 What it is

- Repo: `github.com/umputun/ralphex`. Homepage `ralphex.com`. MIT. ~1.3k stars. Go.
- Created `2026-01-19`. Last push `2026-06-15`.
- Self-description: *Autonomous plan execution with Claude Code. Executes implementation plans task by task in fresh Claude sessions, then runs multi-phase code reviews. Write a plan, start ralphex, walk away.*
- Module: `github.com/umputun/ralphex`. Entry: `cmd/ralphex/main.go` (~61 KB).

### 2.2 Architecture

Single Go binary, package-oriented:

- `cmd/ralphex/main.go` — CLI parsing (`jessevdk/go-flags`), signal/break wiring.
- `pkg/processor/runner.go` — `Runner` with five modes: `ModeFull`, `ModeReview`, `ModeCodexOnly`, `ModeTasksOnly`, `ModePlan`.
- `pkg/processor/phase/` — phase engines: `task.go`, `review.go`, `external_review.go`, `finalize.go`, `plan_creation.go`, `signals.go`, `break_controller.go`, `git_state.go`.
- `pkg/executor/` — process supervision for Claude/Codex CLIs, with `procgroup_unix.go`/`_windows.go` for kill-the-whole-tree semantics.
- `pkg/plan/` — markdown plan parser.
- `pkg/progress/` — append-only log, flock-guarded.
- `pkg/web/` — optional SSE/web dashboard (`--serve`, port 8080).
- `pkg/notify/` — Telegram/email/Slack/webhook/custom-script alerts.
- `scripts/*-as-claude/` — drop-in shims (codex, copilot, gemini, agy, opencode) using the stream-JSON contract.

### 2.3 Task model — markdown headings + checkboxes

Tasks are **`### Task N:` (or `### Iteration N:`) headings with `- [ ]` / `- [x]` checkboxes inside a single plan file**. From `pkg/plan/parse.go`:

```go
var taskHeaderPattern = regexp.MustCompile(`^###\s+(?:Task|Iteration)\s+([^:]+?):\s*(.*)$`)
var checkboxPattern   = regexp.MustCompile(`^\s*-\s+\[([ xX])\]\s*(.*)$`)
```

Plan file default location: `docs/plans/*.md`. Filename → branch name via `ExtractBranchName` (strips date prefix). Multi-plan → `fzf` selector.

**`--plan "<description>"`** is an interactive plan-drafting mode: the model returns a draft inside `<<<RALPHEX:PLAN_DRAFT>>>…<<<RALPHEX:END>>>` sentinels; user accepts/revises in `$EDITOR`/rejects.

### 2.4 Loop mechanics

Outer loop in `TaskPhase.Run`:

```go
for i := 1; i <= p.cfg.MaxIterations; i++ {
    loopCtx, loopCancel := p.breaks.context(ctx) // Ctrl+\ break
    execResult := p.policy.Run(loopCtx, p.exec.Run, prompt, execName)
    if result.Signal == SignalCompleted {
        if p.HasUncompletedTasks() { continue } // verify against plan file
        return nil
    }
    if result.Signal == SignalFailed {
        if retryCount < p.retryCount { retryCount++; sleep(iterationDelay); continue }
        return errors.New("...")
    }
    p.policy.Sleep(ctx, p.iterationDelay)
}
return fmt.Errorf("max iterations (%d) reached without completion", p.cfg.MaxIterations)
```

Defaults: `iterationDelay = 2s`, `MaxIterations = 50`, `retryBackoff = 5s`, `minReviewIterations = 3`, `reviewIterationDivisor = 10`.

**Per-iteration prompt** (verbatim from `pkg/config/defaults/prompts/task.txt`):

> CRITICAL CONSTRAINT: Complete ONE Task section per iteration. … Complete ALL checkboxes in that section, then STOP. Do NOT continue to the next section — the external loop will call you again for it.

### 2.5 Sentinel taxonomy

```go
const (
    Completed  = "<<<RALPHEX:ALL_TASKS_DONE>>>"
    Failed     = "<<<RALPHEX:TASK_FAILED>>>"
    ReviewDone = "<<<RALPHEX:REVIEW_DONE>>>"
    CodexDone  = "<<<RALPHEX:CODEX_REVIEW_DONE>>>"
    Question   = "<<<RALPHEX:QUESTION>>>"
    PlanReady  = "<<<RALPHEX:PLAN_READY>>>"
    PlanDraft  = "<<<RALPHEX:PLAN_DRAFT>>>"
)
```

`ALL_TASKS_DONE` is double-checked against the plan file (`HasUncompletedTasks()`) — model-emitted "done" is verified, not trusted.

### 2.6 Multi-phase review pipeline (`runFull`)

```go
r.phases.task.Run(ctx)              // 1. task loop
r.phases.review.First(ctx)          // 2. Claude review
r.phases.review.Loop(ctx, "")       // 2.1 review loop until clean
r.runExternalAndPostReview(ctx)     // 2.5 external (codex) review → review loop → finalize
```

- **External review** runs `codex` (default) or a `custom_review_script`. Stalemate detected: N consecutive rounds with unchanged HEAD+diff fingerprint terminates the loop (`review_patience`).
- **Post-external Claude review** lets Claude respond to codex's findings.
- **`{{agent:NAME}}` template expansion** in review prompts: under Claude, becomes a Task-tool invocation; under codex, `spawn_agent(agent='ralphex-reviewer', task='...')`. Same template, two executors.

### 2.7 Pluggable executors

`ClaudeExecutor` parses stream-JSON line by line; `RecentText` rolling window (last 10 blocks) is used for sentinel/pattern detection to **avoid false positives on retrospective text discussing rate limits**.

Plug-in surface:
1. **Wrappers** in `scripts/*-as-claude/`: codex, copilot, gemini, agy, opencode — any CLI that emits compatible stream-JSON.
2. **First-class codex executor** via `--codex` flips the entire pipeline. README cites the *June 15 2026 Anthropic billing split between Claude Max and Claude Agent SDK credit pool* as motivation: users stay on existing OpenAI plans.

### 2.8 Guardrails

- **Branch isolation:** `--worktree` runs in an isolated `git worktree` derived from the plan filename. Full and tasks-only modes only.
- **Containerization:** optional via `scripts/ralphex-dk.sh` wrapper. Two images: `ghcr.io/umputun/ralphex:latest` (base) and `…-go:latest`. `--docker` mounts host Docker socket with explicit security warning.
- **Reviewer step:** multi-phase, baked into `runFull`.
- **Rate-limit / 5xx classification:** `PatternMatchError`, `LimitPatternError`, `RetryPatternError`. Rate-limits trigger `--wait`-backed sleep+retry; transient 5xx auto-retry on `claude_retry_patterns`; everything else exits.
- **Timeouts:** `--session-timeout` (wall-clock) + `--idle-timeout` (silence). On timeout, child process-group-killed; iteration retries after `retryBackoff`.
- **Task retry:** `TaskRetryCount` (default 1).
- **Auth hygiene:** `ANTHROPIC_API_KEY` stripped from child env by default to prevent host-key silent-billing. `CLAUDECODE` always stripped.

### 2.9 Observability

- **Progress file** (`pkg/progress/progress.go`) — flock-guarded append-only log; passed to children as `{{PROGRESS_FILE}}` for in-prompt context.
- **Phase enum** (`pkg/status/status.go`): `PhaseTask`, `PhaseReview`, `PhaseCodex`, `PhaseClaudeEval`, `PhasePlan`, `PhaseFinalize`.
- **Web dashboard** — `--serve` (default 127.0.0.1:8080), real-time streaming via SSE. `--watch <dir>` (repeatable) watches multiple progress files for multi-project monitoring.
- **Notifications** — completion/failure alerts via Telegram/email/Slack/webhook/custom-script.

### 2.10 Notable design decisions

- **Plan file is the source of truth.** Model rewrites checkboxes in place. Ralphex re-parses every iteration; completion signal is verified against file, not trusted blindly.
- **Process-group-kill cleanup** — kills the whole subtree on cancel, since Claude Code spawns its own children.
- **Sliding 10-block RecentText window** — sentinel/pattern detection scoped to recent output to avoid false matches on retrospective text.
- **Ctrl+\\ "pause and edit"** — `SIGQUIT` pauses iteration, prompts operator, next iteration re-reads plan file. Operator can edit the plan mid-run.
- **Same prompt → two executors** via `{{agent:NAME}}` template expansion.
- **Mercurial support** via `vcs_command` + `scripts/hg2git/hg2git.sh` shim.

---

## 3. Claude Code `/goal` command (Anthropic)

### 3.1 What it is

- Built-in slash command. Claude Code v2.1.139, May 11 2026.
- Surface: CLI (interactive and `-p` non-interactive), Desktop app, Remote Control.
- Not a plugin/skill/subagent. Session-scoped completion-condition evaluator.

### 3.2 Syntax

```
/goal <condition>          # set a goal
/goal                      # check status (duration, turns, tokens, last reason)
/goal clear                # stop a goal before completion
```

Examples:
- `/goal all tests in test/auth pass and the lint step is clean`
- `/goal CHANGELOG.md has an entry for every PR merged this week`
- `/goal ... or stop after 20 turns`

Conditions ≤4000 chars, free-text, must describe something the transcript can demonstrate.

### 3.3 Mechanics — two-model evaluator pattern

- **Main model:** does the work (user-configured, e.g. Opus).
- **Evaluator model:** checks condition after every turn. **Defaults to Haiku.**

Per turn:
1. Main completes a turn, surfaces output.
2. Haiku checks: does the transcript evidence satisfy the condition?
3. No → Haiku returns reason as guidance; main starts turn N+1 automatically.
4. Yes → goal clears; control returns to user.

**State:** session-scoped; lives in transcript + ephemeral session memory. Active goals **persist** on `--resume`/`--continue` (turn/token counters reset; condition carries over). Achieved/cleared goals not restored.

**Max-step cap:** user-defined via condition clause (e.g. `or stop after 20 turns`). Otherwise unbounded.

### 3.4 What `/goal` is NOT

- **Not a task system.** No backlog, no AC, no task IDs. Pure condition-driven.
- **No sub-task decomposition.** Won't break work into sub-tasks; no built-in awareness of any task model.
- **No branch isolation.** Goal-scope = session-scope; whatever branch you're on stays your branch.
- **No reviewer gate.** Goal clears as soon as the evaluator says yes.
- **No automatic rollback.** Broken state from a turn is not reverted.
- **No cost-cap enforcement.** Must bound via turn-count in the condition.

### 3.5 Where `/goal` fits in the comparison

`/goal` is the *smallest possible* useful Ralph-shaped loop: keep iterating until a condition holds. It's a session-scoped wrapper, not a task orchestrator. Its main contribution to the design space is the **Haiku-evaluator-as-stop-condition** pattern — a cheap, model-driven stop predicate that doesn't require parsing sentinel strings or backlog state.

For Ralph-style structured work — backlog, AC, reviewer gates, branch isolation — `/goal` is the wrong tool. For "run until this measurable thing is true in a single session," it's a clean fit.

### 3.6 Documentation references

- `/goal` command: `https://code.claude.com/docs/en/goal.md`
- Scheduling comparison: `https://code.claude.com/docs/en/scheduled-tasks.md#compare-scheduling-options`
- Hooks and Stop hooks: `https://code.claude.com/docs/en/hooks-guide.md`
- Changelog v2.1.139: `https://code.claude.com/docs/en/changelog.md`

---

## 4. This project (Ralph + Backlog.md)

### 4.1 Orchestrator

- Project shim: `/Users/paul/Private/Projects/ai/ralph/ralph.sh` (6-line `exec` to canonical script).
- Canonical: `~/.claude/skills/ralph-run/scripts/ralph.sh` and project copy at `skills/ralph-run/scripts/ralph.sh` (895 lines).
- Flags: `--tool`, `--model`, `--effort`, `--timeout`, `--on-error`, `--retry-count`, `--log-file`, `--prompt-file`, `--tasks`, `--block-end-buffer-min`, `--devcontainer`, positional `max_iterations` (default 10).
- Per-iteration: usage-check pause gate → pick lowest-ID Done-deps-satisfied To Do task (or whitelist-restricted) → build `MODE: autonomous (Ralph loop iteration N of MAX)` prefix → spawn tool, `tee` to temp file → parse for `<promise>COMPLETE</promise>` and `## Task Summary` blocks → diff `DONE_BEFORE`/`DONE_AFTER` → update status JSON → sleep 2s.

### 4.2 Heartbeat + status JSON

Heartbeat: background subshell touches `backlog/.ralph-heartbeat` every 5s; liveness = `(now - mtime) < 15s`. Status file `backlog/.ralph-status.json` schema covers `pid`, `started_at`, `state` (running/completed/failed/paused), `iteration`, `max_iterations`, `tool`, `tasks_done[]`, `tasks_remaining`, `current_task`, `last_iteration_duration`, `elapsed`, `errors[]` (structured `{iteration, at, message}`), `completed_at`, `exit_code`, `iteration_started_at`, `timeout_sec`, and pause fields (`paused_reason`, `paused_buffer_min`, `paused_remaining_min`, `paused_block_end_time`, `paused_at`).

Double-run guard: startup reads status, exits with PID-named error if state=running + heartbeat fresh.

### 4.3 Skills inventory

- **ralph-run** — launches `ralph.sh` detached; preflight; heartbeat wait; if `watch` set, schedules first `ralph-status-watch` tick via `ScheduleWakeup`.
- **ralph-status** — concise progress summary; reads status + heartbeat; UTC→Moscow conversion via helper.
- **ralph-status-watch** — internal; `ScheduleWakeup` polling chain (self-tracked `tick_count`, 24-tick safety cap). Detection rules a/b/c/d/e/f/g; first match wins; rules e/f terminate.
- **ralph-stop** — graceful kill (`pkill -TERM -P` → poll 10s → `pkill -KILL -P`).
- **ralph-task** — ad-hoc create + edit-deliberation (split/AC rework). 6-rule decomposition heuristic. MUST rules: repeat `--ac` per criterion, may include code blocks, optional `feature:<slug>` label, NO brainstorm-file refs in `-d` (R16).
- **ralph-prd** — PRD authoring; multi-task features with cross-task invariants.
- **ralph-backlog** — PRD → individual backlog tasks; one task per user story; auto-label `feature:<name>`.
- **ralph-review** — cumulative cross-task feature review via `ralph-reviewer` agent.
- **ralph-handoff** — cross-project task handoff with `Source: <abs-path>@<sha>` + before-starting checklist.
- **ralph-sync** — sync `agents/`/`skills/` from project to `~/.claude/`.
- **ralph-init** — bootstrap a new project with templates (R11 parity set).

### 4.4 Agents

- **task-reviewer** (green) — single-task pre-merge review. 8-item checklist + project rules R1–R16 from `.claude/task-reviewer-rules.md`. Verdict: APPROVED / CHANGES REQUESTED.
- **ralph-reviewer** (purple) — cumulative cross-task feature review. Reads PRD + brainstorm + tasks + diff. 5-pass rubric: PRD Coverage / Non-Goal Protection / Brainstorm Scope Cuts / Success-Metric Realism / Out-of-Scope Creep. Verdict: Aligned / Partial / Drifted.

### 4.5 Hooks

- `task-validator.sh` — PostToolUse after `backlog task edit/create`. Validates description, AC, deps, path refs. Recently hardened (TASK-142) with SUBSTANTIVE gate + path-heuristic skip rules.
- `master-branch-guard.sh` — PreToolUse on Edit/Write. Blocks edits on master except for `.claude/`, `design/`, IDE configs, `.gitignore`. Requires `task-*` branch.
- `commit-msg-guard.sh` — blocks AI-attribution trailers.
- `commit-prefix-guard.sh` — enforces commit prefix.
- `naming-guard.sh` — branch naming pattern.
- `notes-guard.sh` — forbids `--notes` (require `--append-notes`).

### 4.6 Devcontainer

- Base `node:20`, optional Stage-1 language runtime.
- Mounts: `${HOME}/.claude` → `/home/node/.claude` (bind), and a **volume overlay** at `/workspace/.claude` populated from a bind-ro `/workspace-host-claude` via `postCreateCommand` — disables sandbox by patching `sandbox.enabled=false` without modifying host settings. This overlay is the source of the recurring `.claude/*` drift bug (4 recurrences: TASK-137/139/141/142).
- Firewall via `init-firewall.sh` + `--cap-add=NET_ADMIN,NET_RAW`. ipset of allowed domains (GitHub IP ranges via meta API, npm, anthropic, sentry, statsig, vscode CDN). Outbound default-deny.

### 4.7 Usage-cap pause

`scripts/usage-check.sh`: invokes `ccusage blocks --active --token-limit max --json`, compares remaining minutes to `BLOCK_END_BUFFER_MIN`. Exit 0=continue, 1=pause (stdout `block_end_in_<rem>min_below_<buffer>min_buffer`), 2=cannot-measure (warn once). `_check_usage_or_pause()` in ralph.sh writes state=paused + paused_reason/buffer/remaining/block_end_time/paused_at to status JSON. Resumable via `/ralph-run`.

### 4.8 Task lifecycle (CLAUDE.md verbatim)

1. **Gate** — verify backlog task exists and is "In Progress".
2. **Plan** — read task, AC, code. `--append-notes "Plan: ..."`.
3. **Implement** — write code, run build/lint/tests, `--check-ac N`.
4. **Review** — spawn `task-reviewer` agent (NOT `general-purpose`) on `git diff master..HEAD`. Do not proceed without APPROVED.
5. **Done** — final build+lint+tests pass. `-s "Done" --append-notes`.
6. **Merge** — commit task file, `git checkout master && git merge <branch> && git branch -d <branch>`.

### 4.9 Reviewer rules R1–R16 (project-specific)

R1 review the diff not the worktree · R2 every AC checked or explicitly deferred · R3 agent files require valid YAML frontmatter · R4 frontmatter changes don't take effect mid-session · R5 GNU/BSD tool portability · R6 no over-broad shell perms · R7 no AI-attribution trailers · R8 hook commands reference scripts not inline bash · R9 git is truth not worktree · R10 don't bypass master-branch-guard · R11 template parity (`.claude/` ↔ `skills/ralph-init/templates/`) · R12 markdown deliverables logically consistent · R13 rationalization not exemption · R14 content preservation during moves · R15 PostToolUse hooks must emit JSON via hookSpecificOutput · R16 task `-d` must not reference brainstorm files.

---

## 5. Side-by-side comparison

| Dimension | Huntley canonical | ralphex (Umputun) | `/goal` (Anthropic) | This project |
|---|---|---|---|---|
| **Form factor** | ~5 lines bash | Go binary (~10k LOC) | Built-in slash command | Bash (~900) + skills + CLI integration |
| **Task model** | `PROMPT.md` + `fix_plan.md` + `AGENT.md` + `specs/*` + `specs/stdlib/*` (markdown) | `### Task N:` + `[ ]` checkboxes in plan file | None — single condition | `backlog.md` CLI (file-per-task w/ frontmatter) |
| **Loop bound** | None (`while :`) | `--max-iterations` (default 50) | User-defined via condition clause | `max_iterations` (default 10 via skill, 50 via CLI) |
| **Iteration delay** | None | 2s | None | 2s |
| **Fresh context per iteration** | Yes | Yes | No (single session) | Yes |
| **State storage** | `specs/`, git, `PROMPT.md` | Plan file rewrites + progress log | Session transcript (ephemeral) | `backlog/tasks/*.md`, git, status JSON |
| **Stop signal** | None (manual kill) | `<<<RALPHEX:ALL_TASKS_DONE>>>` etc. (7 sentinels) | Haiku evaluator on condition | `<promise>COMPLETE</promise>` + empty To Do |
| **Stop verification** | None | Re-parse plan file (sentinel + ground truth) | Evaluator-judged | Backlog re-query |
| **Branch isolation** | No (long-lived feature branch) | `--worktree` per plan | No | Per-task `task-<id>` branch |
| **Reviewer gate** | None | Multi-phase: Claude → external codex → Claude | None | Mandatory `task-reviewer` per task |
| **Cumulative review** | None | Stalemate-detected on external | None | `ralph-reviewer` for cross-task feature review |
| **Containerization** | Not in canonical /ralph/ post | Optional Docker wrapper | Inherits session | Built-in devcontainer w/ firewall |
| **Sandboxing** | Not discussed in /ralph/ | Strips `ANTHROPIC_API_KEY` from child env | Parent session config | Firewall ipset for outbound; devcontainer w/ NET_ADMIN |
| **Heartbeat / liveness** | No | Process-group + idle-timeout | N/A | 5s touch file, 15s freshness |
| **Status / observability** | None | Web dashboard (`--serve`), progress file, phase enum, multi-project `--watch` | Status panel in session | JSON status file, `ralph-status`/`ralph-status-watch`, structured `errors[]` |
| **Watch / monitor pattern** | None | SSE web dashboard | In-session UI | `ScheduleWakeup`-driven chain w/ 24-tick safety cap |
| **Notifications** | None | Telegram/email/Slack/webhook/script | None | None |
| **Cost / usage** | Economic only ($297 vs $50k contract) — no Max/overnight in /ralph/ | Rate-limit detection + `--wait`; no cap pause | Manual via turn-count clause | `--block-end-buffer-min` via `ccusage`; pause+resume |
| **Pattern-based retry** | No | Rate-limit / transient 5xx / fatal classification | No | No (single `--on-error` policy) |
| **Pluggable executor** | Hard-code in shell | `--codex` + 5 wrapper shims | No (single model + Haiku evaluator) | `--tool claude\|opencode` |
| **Plan authoring inside loop** | No | `--plan "<desc>"` interactive draft | No (chat-driven) | `ralph-prd` + `ralph-brainstorm` (separate skills) |
| **Multi-language portability** | Shell-only | Cross-platform Go (Win/Linux/macOS) | All Claude Code surfaces | Shell (macOS/Linux) |
| **Code review philosophy** | Trust tests | External LLM + cumulative + stalemate | None | `task-reviewer` per task + `ralph-reviewer` per feature |
| **Auth hygiene** | n/a | Strip `ANTHROPIC_API_KEY` from child env by default | N/A | n/a |
| **Process cleanup** | Shell exits | Process-group kill | Session-bound | `pkill -TERM -P` → `pkill -KILL -P` |
| **Resume semantics** | Just rerun | Re-reads plan file mid-run on `SIGQUIT` | `--resume` carries condition, resets metrics | Pause-state in JSON; `/ralph-run` resumes |

---

## 6. Recommendations for this project

Ranked by ROI (impact ÷ effort), with concrete task shapes. Each is a defensible "what to borrow and why."

### 6.1 HIGH — borrow a richer signal taxonomy from ralphex

**Today:** single sentinel `<promise>COMPLETE</promise>` + heuristic on `## Task Summary` count.

**Proposed:** dedicated sentinels for distinct outcomes:

```
<ralph:task-done id="TASK-NNN" />          # one task completed cleanly
<ralph:task-failed id="TASK-NNN" />        # one task failed; ralph.sh decides retry vs abort
<ralph:question text="..." />              # ask operator; ralph.sh writes to status JSON, pauses
<ralph:all-done />                         # backlog empty (replaces <promise>COMPLETE</promise>)
```

**Why:** today, `ralph-status-watch` can't distinguish "iteration succeeded" from "iteration failed but next will retry" without scraping prose. A clean sentinel surface lets the watch chain emit accurate state transitions without false positives. Ralphex's `RecentText` rolling window + double-check against ground truth (re-query backlog) is the right pattern.

**Cost:** modest. Update CLAUDE.md autonomous-mode contract + ralph.sh parsing + ralph-status-watch detection rules. Backward-compat via grace period (accept both old `<promise>` and new sentinels).

**Effort:** 1 task (~6 AC). Touches CLAUDE.md, `ralph.sh:780-820` (signal parsing), `skills/ralph-status-watch/SKILL.md` detection rules.

---

### 6.2 HIGH — external-reviewer pass with a different model

**Today:** single `task-reviewer` agent (same model family as the implementer) per task.

**Proposed (ralphex pattern):** after `task-reviewer` APPROVED but BEFORE merge, run a second-pass review with an explicitly different model (e.g., Haiku for cheap broad sanity-check, or codex CLI if available). On disagreement, surface to operator.

**Why:** the Huntley-acknowledged failure mode — *agent deletes/weakens tests to make them pass* — survives single-model review because the reviewer agent and implementer share systematic blind spots. Ralphex's experience suggests cross-model review catches a different failure class. Stalemate detection (HEAD+diff fingerprint unchanged for N rounds) bounds the cost.

**Cost:** moderate. Requires a new agent definition + integration into Task Lifecycle Step 4. Stalemate detection adds ~30 lines to ralph.sh.

**Effort:** 1–2 tasks. Optional/opt-in via flag initially.

---

### 6.3 MEDIUM — worktree isolation per task

**Today:** per-task **branch** in a single working tree. Devcontainer volume overlay at `/workspace/.claude/` has caused 4 recurrences of state drift (TASK-137/139/141/142).

**Proposed (ralphex `--worktree` pattern):** each task gets a fresh `git worktree add` under `.ralph-worktrees/task-<id>/`. After merge, worktree is removed. Status JSON tracks worktree path.

**Why:**
- Eliminates volume-overlay drift entirely — `.claude/` lives outside the worktree.
- Concurrent tasks become possible (relevant for the agent fleet pattern even if not used today).
- Failed iteration cleanup is `rm -rf worktree` instead of `git restore` archaeology.

**Cost:** moderate. Touches the autonomous-mode branch-creation step + devcontainer mount config + ralph-status-watch (worktree path field).

**Risks:** Backlog.md state lives at the repo root — worktrees see the same `backlog/tasks/` directory, so concurrent edits could conflict. Need to test.

**Effort:** 1 spike task to validate, then 1–2 implementation tasks.

---

### 6.4 MEDIUM — pattern-based retry classification

**Today:** `--on-error stop|continue|retry` is a single policy. Doesn't distinguish rate-limit (sleep+retry forever) from transient 5xx (auto-retry briefly) from fatal (exit).

**Proposed (ralphex pattern):** classify errors:

- **LimitPatternError** (`hit your limit`, `quota exceeded`) → respect `--block-end-buffer-min` style wait, no retry count limit, write `state=paused`.
- **RetryPatternError** (`API Error: 5(0[234]|29)`, `transient_timeout`) → auto-retry up to N, then escalate.
- **FatalPatternError** → exit with structured error in status JSON.
- **Unknown** → current behavior.

**Why:** current single-policy treats a 503 the same as a syntax error. Operator gets paged for transients; legitimate fatal errors get swallowed in `retry` mode.

**Cost:** small. Pattern config in `ralph.sh` (~50 lines, can use bash arrays).

**Effort:** 1 task (~5 AC).

---

### 6.5 MEDIUM — `--plan` interactive draft mode

**Today:** plan authoring is a separate skill chain (`ralph-prd` → `ralph-backlog`). For ad-hoc work, the user invokes `ralph-task`.

**Proposed (ralphex `--plan` pattern):** add an "interactive plan" mode to `/ralph-run` that, on launch, drafts a backlog plan from a free-text description, lets the user accept/revise/edit in `$EDITOR`/reject, **then** starts the loop. Reduces friction for ad-hoc multi-task work where the existing skill chain is too heavy.

**Why:** today's pipeline is well-suited to deliberate feature work (PRD → backlog → review) but heavy for "I just want Ralph to do these five small things." The `ralph-task` skill handles single tasks. There's a gap for "draft a quick mini-plan, then loop on it."

**Cost:** small-to-moderate. Could be a new skill (`ralph-quickplan`) rather than a flag.

**Effort:** 1 task.

**Open question:** does this duplicate `ralph-task` + autonomous mode enough to be redundant? Worth a design discussion.

---

### 6.6 LOW — notifications

**Today:** none. Operator must check `/ralph-status` or watch via `ralph-status-watch`.

**Proposed:** opt-in Telegram/webhook notification on `state=completed/failed/paused`. Ralphex ships Telegram/email/Slack/webhook/script — cheap to copy.

**Cost:** small. Could be a `--notify <webhook-url>` flag or a `notify.sh` hook in `.claude/hooks/`.

**Effort:** 1 task. Probably opt-in via env var.

---

### 6.7 LOW — `/goal`-style optional stop condition

**Today:** stop = empty backlog or `<promise>COMPLETE</promise>`.

**Proposed:** add `--stop-when "<condition>"` to ralph.sh that, when set, evaluates a stop condition via a small model (Haiku) after every iteration — separate from backlog exhaustion. Useful for "run until prod test suite passes" or "run until p95 < 200ms in last benchmark output."

**Why:** complements task-based loops. Backlog-based stop is the right primary model; goal-condition is a useful escape hatch.

**Cost:** small. Calls `claude -p --model haiku` with the condition + last iteration output.

**Effort:** 1 task. Low priority; nice-to-have.

---

### 6.8 LOW — strip `ANTHROPIC_API_KEY` from child env by default

**Today:** ralph.sh inherits full env into the spawned tool.

**Proposed:** strip `ANTHROPIC_API_KEY` and `CLAUDECODE` before spawning the child, unless `--preserve-anthropic-api-key`/`--preserve-claudecode` is set.

**Why:** ralphex's stated rationale is sound — a host-set API key can silently bill the wrong account, especially after the June-2026 Anthropic billing split. This project routes through Claude Max via subscription auth; an env API key would bypass that.

**Cost:** trivial (one line).

**Effort:** half a task. Bundle with another change.

---

### 6.9 NEUTRAL — things to KEEP (already better than the alternatives)

- **Heartbeat liveness via file mtime.** Better than ralphex's process-group check inside containers (where pids are namespaced and unreliable).
- **Structured `errors[]` array in status JSON.** Better than ralphex's append-only progress log for programmatic consumption.
- **`ScheduleWakeup`-driven watch chain with 24-tick safety cap.** Native Claude Code idiom; better integrated than ralphex's web dashboard for the in-conversation use case.
- **Brainstorm distillation contract (R16).** ralphex has no equivalent — its plan files are the contract. This project's separation of human-design-history (brainstorm) from implementer-contract (task `-d`) is a real innovation worth keeping.
- **Per-task branches + mandatory `task-reviewer`.** Tighter than ralphex's per-plan worktree + multi-phase review.
- **Usage-cap pause via `ccusage`.** ralphex addresses rate-limits reactively; this project handles them proactively at the block boundary.

---

## 7. Open questions for the operator

1. **Should we file `/ralph-quickplan`** as a follow-on to ralph-task, or expand ralph-task itself with a multi-task mode? (Affects §6.5 scoping.)
2. **Cross-model reviewer:** Haiku, codex, or opt-in operator choice? (Affects §6.2 scoping.)
3. **Worktree feasibility spike:** is the backlog/tasks shared-state collision a blocker? (Need a quick test before committing to §6.3.)
4. **Notification surface:** Telegram (broadest, requires bot setup) or generic webhook (simplest)? (Affects §6.6 scoping.)
5. ~~**Provenance verification:** the Huntley research agent couldn't reach the live web; direct quotes in §1 are paraphrased from training. Want a follow-up pass with web access enabled?~~ **Resolved** by TASK-146 — §1 re-fetched against `ghuntley.com/ralph/` on 2026-06-21; §1.7 enumerates what was removed. The visible portion of `/specs/` is paywalled; one residual unknown is whether claims about containerization/`--dangerously-skip-permissions` live in paywalled material elsewhere.

---

## 8. References & provenance

### External primary sources (cited)
- Huntley canonical: `https://ghuntley.com/ralph/` (**fetched 2026-06-21 via WebFetch; §1 quotes are verbatim from this fetch**)
- Huntley spec-driven companion: `https://ghuntley.com/specs/` (**fetched 2026-06-21; body is paywalled — only excerpt visible**)
- ralphex: `https://github.com/umputun/ralphex` (read by research agent)
- ralphex llms.txt: `https://raw.githubusercontent.com/umputun/ralphex/master/llms.txt`
- ralphex source (cited inline in §2): `cmd/ralphex/main.go`, `pkg/processor/runner.go`, `pkg/processor/phase/task.go`, `pkg/plan/parse.go`, `pkg/executor/executor.go`, `pkg/status/status.go`, `pkg/config/defaults/prompts/task.txt`, `pkg/processor/phase/git_state.go`
- Claude Code `/goal`: `https://code.claude.com/docs/en/goal.md`, `https://code.claude.com/docs/en/scheduled-tasks.md#compare-scheduling-options`, `https://code.claude.com/docs/en/hooks-guide.md`, `https://code.claude.com/docs/en/changelog.md`

### This project (read directly)
- `README.md` (self-description, citations to Huntley + Carson)
- `CLAUDE.md` (Autonomous Mode + Task Lifecycle)
- `ralph.sh` shim + `skills/ralph-run/scripts/ralph.sh` (895 lines)
- `.claude/task-reviewer-rules.md` (R1–R16)
- `.claude/hooks/*` (6 hooks)
- `.devcontainer/devcontainer.json` + `Dockerfile` + `init-firewall.sh`
- `skills/ralph-*/` (10 skills) + `agents/{task,ralph}-reviewer.md`
- `backlog/.ralph-status.json` (live status, 18 fields)

### Provenance caveats
- **§1 (Huntley):** §1.1–1.6 now sourced from a direct WebFetch of `https://ghuntley.com/ralph/` on 2026-06-21. Direct quotes are verbatim from that fetch. §1.7 explicitly enumerates the claims that were removed because they could not be verified against the canonical post or the visible portion of the /specs/ companion (paywalled). The matrix in §5 was adjusted in four rows (Task model, Containerization, Sandboxing, Cost/usage) to match the verified content.
- **§2 (ralphex):** research agent read raw source via `raw.githubusercontent.com`. Function names, regexes, sentinel strings, and constants are accurate to the time of fetch (~`2026-06-15` push, fetched today `2026-06-21`).
- **§3 (`/goal`):** research agent fetched official Anthropic docs. Release version (v2.1.139, May 11 2026) and changelog cited.
- **§4 (this project):** research agent read the local repo at HEAD `305b296` (pre-TASK-145); §1 verification work was performed on `task-146-verify-huntley` branched off HEAD `fb42229`.
