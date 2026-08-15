---
id: doc-5
title: Task Execution Lifecycle and Push Mechanisms
type: guide
created_date: '2026-08-15 19:45'
---

# Task Execution Lifecycle and Push Mechanisms

A navigation and reference sheet for how one unit of work travels through this repository: from the moment an intent is admitted as a backlog task, through the per-task execution loop, to completion, and out through the several "push" channels by which Ralph propagates state and updates downstream. The canonical rules live in `CLAUDE.md` (the Task Lifecycle) and `README.md`; the mechanics live in the cited source files. This doc ties them together and is intentionally not a duplicate of either — where they disagree, they win.

## Lifecycle at a glance

```
  1. INTENT ADMISSION       2. EXECUTION              3. COMPLETION & MERGE      4. PUSH / PROPAGATION
  --------------------      ------------------        ---------------------      ---------------------
  task created, or          Gate   (In Progress)      bump-version.sh --auto     post-commit stamping
    selected, or            Plan   (append-notes)     commit task file             (per commit, local)
    handed off              Implement (build/         git merge --no-ff          git push origin master
  run-mode gate               lint/test + AC)         bump-version.sh --tag        (post-loop, default-on)
    (interactive only)      Review (task-reviewer)      -> vX.Y.Z tag            version-bump governance
  autonomous selection      Done                      git branch -d <branch>       + push.followTags
                                                                                   + pre-push guard
                                                                                 /plugin update (marketplace)
                                                                                 /ralph-handoff (cross-project)
                                                                                 status file + heartbeat
```

Each iteration is a fresh AI instance with clean context; the only memory carried between iterations is git history, backlog task notes, and the `CLAUDE.md` / `AGENTS.md` files.

## 1. Intent admission

"Admission" is the boundary where an intent becomes a runnable backlog task and gets picked up for execution.

### Where tasks come from

- **Brainstorm -> PRD -> backlog.** For substantial features: `/brainstorm` converges on architecture and a "Distilled for ralph-task" block, `ralph-prd` writes `design/<name>-prd.md`, and `ralph-backlog` converts it into individual tasks with acceptance criteria, priorities, and dependencies.
- **`ralph-task` (ad-hoc).** For one-off task creation and judgment-bearing edits (split, add-as-AC, rework vague AC). Copies the distilled block verbatim into the task `-d`; the brainstorm itself never appears in a task body (the producer/consumer contract enforced by rule R16).
- **`ralph-handoff` inbox (cross-project inbound).** A task deposited into this project's `backlog/tasks/` by another Ralph project's `/ralph-handoff`. It carries a `Source: <abs-path>@<sha>` line and a "Before starting" validation checklist, and lands untracked with status `To Do`. See section 4.5 for the outbound side.

### How a task is selected to run

- **Autonomous mode.** When the prompt starts with `MODE: autonomous`, the loop completes exactly ONE task, then STOPs; the Ralph loop spawns a fresh instance for the next one. If the prompt names a task, only that task is worked; otherwise the agent runs `backlog task list -s "To Do" --plain` and picks the lowest-ID task whose dependencies are all `Done`. When no `To Do` tasks remain the agent emits `<promise>COMPLETE</promise>` and the loop exits.
- **Named / whitelisted.** `/ralph-run tasks=<ids>` (or the shim's `--tasks`) constrains the run to specific numeric task IDs.

### The Implementation Mode Gate (interactive sessions only)

In an interactive session, before implementing ANY task — and before creating a `task-*` branch or writing code — the agent asks (via `AskUserQuestion`, header `Run mode`) how to run it:

- **Ralph (default / recommended)** — launch `/ralph-run tasks=<id> watch=5m devcontainer=true`; Ralph branches, implements, reviews, and merges autonomously. Do NOT pre-set task status; Ralph manages it.
- **Interactive** — branch (`git checkout -b task-<id>`) and run the Task Lifecycle in the current session.

Carve-outs — the gate never fires for: `MODE: autonomous` runs (the loop is already the execution mode), and mechanical / edit-deliberation ops (status changes, AC checks, `--append-notes`, label/priority/dependency edits, task creation / splitting / AC rework). On an `AskUserQuestion` failure or an unparseable answer, the agent stops and asks in plain text rather than silently branching.

### Handoff acceptance gate

When the user asks "check new task TASK-N — do you understand, can you run it?", a `Source:`-carrying task triggers a green/yellow/red validation gate: read the body in full, run the "Before starting" checklist literally (every `(exists)` path present, every AC objectively pass/fail, all frontmatter deps `Done`, out-of-scope items not pulled in), then report. Work does not start until the user confirms after a green or clarified-yellow report. This gate applies even under autonomous mode — a `Source`-carrying task pulled by the selector runs the checklist first and stops on red.

## 2. Execution — the Task Lifecycle

Once a task is admitted, execution follows the six-step Task Lifecycle in `CLAUDE.md`. Steps 1-5 are the execution phase; step 6 (Merge) is treated separately in section 3.

1. **Gate.** Verify the task exists and is `In Progress` — create or update status first.
2. **Plan.** Read task, AC, and relevant code. Record the plan: `backlog task edit <id> --append-notes "Plan: ..."`.
3. **Implement.** Write code; run build / linter / tests; check off AC with `backlog task edit <id> --check-ac <n>`.
4. **Review.** After tests pass, spawn the `task-reviewer` agent (not `general-purpose`) on `git diff master..HEAD`. Do NOT proceed to Done or Merge without an APPROVED verdict. The reviewer applies an 8-item checklist plus this repo's custom rules R1-R16 in `.claude/task-reviewer-rules.md`.
5. **Done.** Final build + lint + tests must pass. `backlog task edit <id> -s "Done" --append-notes "..."`.

Structural invariants of the execution phase:

- **Per-task branching.** Every change needs a backlog task and a `task-*` branch (the `master-branch-guard.sh` PreToolUse hook blocks edits to project files on `master`). One task per iteration, one branch per task, branched from `master`.
- **Fresh context.** Each iteration spawns a new AI instance with clean context; memory persists only through git history, task notes, and `CLAUDE.md` / `AGENTS.md`.
- **Feedback loops.** Build / typecheck, linter, tests, and mandatory code review are the loops that keep the loop honest — broken code compounds across iterations, so a task may ONLY be marked `Done` when build, tests, linter, AND review all pass.
- **Quality bar for this repo.** Lint is `uv run ruff check .`; tests are `uv run pytest`; shell scripts must satisfy R5 GNU/BSD portability.

## 3. Completion and merge

Step 6 of the Task Lifecycle turns an approved task branch into canon on local `master`. It is repo-specific plugin-marketplace governance (the helper lives only under `.claude/` and is NOT mirrored to `ralph-init` templates):

- **(a)** On the task branch, run `.claude/hooks/bump-version.sh --auto` — it auto-bumps the plugin version in BOTH manifests and commits iff a shipped `plugins/ralph/**` file changed in `master..HEAD`, else no-ops (see section 4.3).
- **(b)** Commit the task file.
- **(c)** `git checkout master && git merge --no-ff <branch>` (an explicit `Merge task-N: <recap>` commit).
- **(d)** On `master`, run `.claude/hooks/bump-version.sh --tag` — it annotates the merge commit `vX.Y.Z` for the current version (no-op if the tag exists) and ensures `push.followTags=true` so the tag rides the next push.
- **(e)** `git branch -d <branch>`.

At this point the work is canon on LOCAL `master`. Making it visible to anything reading the GitHub remote is the job of the push mechanisms below.

## 4. Push and downstream-propagation mechanisms

"Push" in this project is not one action — it is several distinct channels, each moving a different kind of state to a different destination. This section enumerates every real one. (Note: `/ralph-sync` appears only in historical `design/` notes; there is no live sync skill or script, so it is not a mechanism here.)

### 4.1 Post-commit hash stamping (per commit, local audit trail)

Source: `.git/hooks/post-commit` (shipped template: `plugins/ralph/skills/ralph-init/templates/git-hooks/post-commit`).

On every commit on a `task-*` branch, the hook appends `Commit: \`<short-sha>\` - <subject>` to the task file's Notes via `backlog task edit --append-notes`, building an audit trail linking commits to tasks. On an amend it replaces the previous entry in place (`sed`); if only `backlog/` files changed it exits early to avoid noise. This is why lifecycle edits must use `--append-notes` (never `--notes`, which the `notes-guard.sh` hook blocks) — they must not clobber hook-generated content. In THIS repo the hook also appends a non-blocking `bump-version.sh --nudge` (see 4.3). This channel is local: it never leaves the repo on its own.

### 4.2 Post-loop publish to origin (`git push origin master`)

Source: `plugins/ralph/skills/ralph-run/scripts/ralph/push.py`, called from `loop.py`.

The loop merges each task branch to LOCAL `master` (the agent runs `git checkout master && git merge` per step 6c; `loop.py` itself never merges). Because a merge only becomes canon for downstream consumers once it reaches `origin/master`, the orchestrator publishes `master` to `origin` automatically once the loop finishes — via `maybe_push_after_loop()`. Publish is ENABLED BY DEFAULT and gated on three independent conditions, ALL of which must hold:

1. **Not opted out** — neither `--no-push` (CLI) nor a truthy `RALPH_NO_PUSH` env var (`push_enabled()`).
2. **Origin exists** — an `origin` remote is registered (`has_origin_remote()`).
3. **Master advanced** — the `git rev-parse master` SHA snapshotted before the loop differs from the SHA after it.

When any gate fails the run skips cleanly: no push, no error, exit code untouched. When a push IS attempted and fails, the failure is surfaced loudly — logged to stderr AND reported via a non-zero exit code — never swallowed. Opt out for a single run with `--no-push` or `RALPH_NO_PUSH=1`.

### 4.3 Version-bump governance (`push.followTags` + pre-push guard)

This repo is its own plugin marketplace. Claude Code runs the plugin's skills from an on-disk cache at `~/.claude/plugins/cache/dddpaul-ralph/ralph/<version>/`, and `/plugin update` rebuilds that cache ONLY when it detects a new version. The plugin version is therefore the cache-refresh trigger, and it must move whenever shipped files change — otherwise every consumer silently keeps running the old cached skills.

- **Shipped set** (a change here requires a strictly-greater version): `plugins/ralph/skills/**`, `plugins/ralph/agents/**`, `plugins/ralph/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`. Excluded: `README`, `design/`, `backlog/`, `.claude/`. The predicate lives once in `.claude/hooks/lib/shipped-set.sh`, shared by the auto-bump helper and the guard so the two cannot drift.
- **Two manifests, kept equal.** The gating `version` lives in both `plugins/ralph/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`; `bump-version.sh` writes both.
- **`bump-version.sh --auto`** (task branch, pre-merge) — bumps iff a shipped path changed in `master..HEAD`; infers the increment (a newly-added skill dir or agent file -> minor; otherwise patch; major never auto), sets both manifests to `(local master version + increment)`, and commits a `task-N: bump plugin version ...` line. Idempotent: no-op when nothing shipped changed or HEAD is already ahead.
- **`bump-version.sh --tag`** (master, post-merge) — sets `git config push.followTags true` and creates the annotated tag `vX.Y.Z` on HEAD (no-op if present). The tag then rides the normal `git push origin master`.
- **`bump-version.sh --nudge`** — non-blocking reminder emitted by the post-commit hook when HEAD touched shipped files but the version is not yet ahead of `master`. Always exits 0.
- **Pre-push guard.** `.git/hooks/pre-push` is a thin wrapper that execs the tracked, reviewable `.claude/hooks/version-bump-guard.sh`. On a push of `master`, if any shipped-set file changed between the remote tip and the pushed tip without a strictly-greater version (`sort -V`), the push is BLOCKED. Non-master pushes, ranges touching no shipped file, and the first push (remote all-zeros) pass through. It enforces monotonic-only, not a specific increment size. This guard is project-specific to this producer repo and is intentionally NOT part of the `ralph-init` template tree.

The current plugin version is `0.3.3`. Increment discipline (human convention): patch for fixes and in-skill edits, minor for a new/removed/renamed skill/agent/flag, major deferred to a future stable-surface declaration.

### 4.4 Plugin-marketplace refresh (`/plugin update`)

This is how a shipped change actually reaches other projects. Once the bumped version is pushed to `origin/master`, consumers run `/plugin marketplace update dddpaul-ralph` then `/plugin update ralph@dddpaul-ralph` to pull the new version and rebuild their skill cache. Sections 4.2 and 4.3 exist to guarantee this step always has a new version to rebuild from.

### 4.5 Cross-project push (`/ralph-handoff`)

Source: `plugins/ralph/skills/ralph-handoff/SKILL.md`.

`/ralph-handoff` pushes a single self-contained task from this project into a DOWNSTREAM Ralph project's `backlog/tasks/` (via `backlog task create`), translating file paths into the destination's frame and attaching a `Source: <abs-path>@<sha>` back-reference (from `git describe --always --dirty --abbrev=12`) plus the "Before starting" validation checklist. The new task lands as `To Do` and is left untracked and uncommitted — the destination user decides whether and when to commit. It is one-way: the handoff does not run the task or sync status back. The receiving side of this channel is the handoff acceptance gate in section 1.

### 4.6 State surfaces external consumers read (status file + heartbeat)

Not a push in the git sense, but the channel by which live run-state propagates to observers. Ralph writes `backlog/.ralph-status.json` on every state change (pid, state, iteration, tasks_done, current_task, errors, exit_code, ...) and touches `backlog/.ralph-heartbeat` every 5 seconds. Dashboards, scripts, and the `ralph-status` / `ralph-status-watch` skills read these to track progress and liveness (a heartbeat older than 15s means dead, regardless of the status file).

## Push mechanisms summary

| Channel | Trigger | Destination | Mechanism |
|---------|---------|-------------|-----------|
| Post-commit stamping | every commit on a `task-*` branch | task file Notes (local) | `backlog task edit --append-notes "Commit: ..."` |
| Post-loop publish | loop finish, default-on | `origin/master` | `git push origin master` after 3 gates pass (`push.py`) |
| Version tag | `bump-version.sh --tag` on master | `origin` + `vX.Y.Z` tag | `push.followTags=true` + `git tag -a` |
| Pre-push guard | `git push origin master` | (blocks the push) | reject if shipped files changed without a strictly-greater version |
| Marketplace refresh | consumer runs `/plugin update` | other projects' skill cache | rebuild triggered by new plugin version |
| Cross-project handoff | `/ralph-handoff` | downstream project `backlog/tasks/` | `backlog task create` + `Source:` line + checklist |
| Status / heartbeat | every state change / 5s | `backlog/.ralph-status.json`, `.ralph-heartbeat` | file writes read by dashboards and status skills |

## File reference index

| File | Role |
|------|------|
| `CLAUDE.md` | Canonical Task Lifecycle, autonomous mode, Implementation Mode Gate, handoff inbox |
| `README.md` | Workflow, dual mode, "Publishing to origin", "Releasing plugin updates" |
| `plugins/ralph/skills/ralph-run/scripts/ralph/push.py` | Post-loop publish (`maybe_push_after_loop`, `push_enabled`, 3 gates) |
| `plugins/ralph/skills/ralph-run/scripts/ralph/loop.py` | Snapshots master before the loop; calls the push module after |
| `.claude/hooks/bump-version.sh` | `--auto` / `--tag` / `--nudge` version governance |
| `.claude/hooks/version-bump-guard.sh` | Pre-push guard (blocks unbumped shipped-file pushes) |
| `.claude/hooks/lib/shipped-set.sh` | Single-source `is_shipped` predicate |
| `.git/hooks/post-commit` | Task-hash stamping (+ nudge in this repo) |
| `.git/hooks/pre-push` | Wrapper that execs `version-bump-guard.sh` |
| `plugins/ralph/skills/ralph-handoff/SKILL.md` | Cross-project outbound task push |
| `plugins/ralph/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | The two version manifests kept equal |
