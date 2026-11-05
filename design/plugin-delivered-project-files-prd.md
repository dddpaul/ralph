---
export: true
title: 'PRD: Plugin-Delivered Project Files and Shared-Backlog Protocol'
type: design
---

# PRD: Plugin-Delivered Project Files and Shared-Backlog Protocol

## 1. Introduction

ralph-init copies the Claude guard hooks, the git hooks and the common allow rules into every project, and `ralph-init upgrade` refreshes them.

**The cost with two hosts.** Each project has one clone per host, and the clones share one origin. Every template change then means an upgrade per project and per clone, and two upgrades of the same project make diverging commits.

**Duplicate task IDs.** Two clones of one origin can also allocate the same task ID. The duplicate arrives with no git conflict and blocks the backlog until it is repaired.

This feature does two things:

- **It moves the Claude guards and the git hook bodies into the ralph plugin,** so a plugin update reaches every migrated project on a host. Each project keeps:
  - a tracked ownership marker;
  - per-clone switches;
  - fixed shims that find the installed plugin through Claude Code's plugin registry.
- **It adds an opt-in shared-backlog protocol,** ported from a sibling project's proven stage-1 script and hardened after review. In an opted-in project, the push to origin decides which task IDs and claims are real.

`design/plugin-delivered-project-files-brainstorm.md` holds the design, its evidence and its decisions. That is the base design plus two dated addenda. This PRD was revised after an external review of its first draft.

## 2. Goals

- **No per-project run for guard and hook changes.** After a project's one-time migration, a plugin release that changes a guard or a git hook needs no run per project or per clone. A plugin update on the host is enough.
- **No diverging commits.** The per-clone part of the migration never commits.
- **The installed version, or a refusal.** Git hook shims and `ralph.sh` run the installed plugin version picked through the registry. A git hook in an enforcing clone refuses rather than guesses when the plugin cannot be resolved.
- **No duplicate IDs on origin.** In opted-in projects, a task ID is published before anyone sees it, and a duplicate never reaches origin.
- **No shared tasks.** Two hosts never start the same task in an opted-in project.
- **Nothing breaks in between.** At every intermediate commit of this feature, projects that have not migrated keep working, and so does this repo.

## 3. Conventions for the stories

- **Ownership.** Each story becomes one backlog task, sized for one Ralph iteration.
- **Host checks.** **(host)** marks a criterion that can be checked only outside the devcontainer, on a real host with the installed plugin:
  - A Ralph run leaves it unchecked and notes "deferred to host".
  - The task does not count as complete until the host check is recorded in its notes and the criterion is checked.
  - Checks that need a broken or unusual plugin registry use an isolated `CLAUDE_CONFIG_DIR` and test clones, never the user's real config.
- **Checks.** "Checks pass" means the parts of `uv run ruff check .`, `uv run pytest` and `LC_ALL=C bats tests/unit` that the story touches.
  - Shell stories also run `bash -n` and the bash 3.2 static guard (`tests/python/test_bash32_syntax.py`) on every shell file they change.
  - Real execution under `/bin/bash` 3.2 is a **(host)** criterion, because the devcontainer has no bash 3.2.
- **Paths.** Paths that do not exist yet are written without backticks.

## 4. User Stories

### Plugin-delivered files

#### US-001: Registry resolver for the installed plugin

**Description:** As a Ralph user, I want shims and `ralph.sh` to run the plugin version Claude Code actually installed, so that a leftover cache folder or a fork called `ralph` is never picked.

**Acceptance Criteria:**

- [ ] **One source.** The resolver block lives in plugins/ralph/skills/ralph-init/templates/shims/resolve-plugin.sh. A test fails when any shim template, `ralph.sh` or `refine.sh` embeds a different copy of it.
- [ ] **Registry lookup.**
  - It reads `<config>/plugins/installed_plugins.json` with jq and requires `version` 2.
  - It selects `plugins["ralph@dddpaul-ralph"]`.
  - It takes the first entry, in registry array order, that applies to the clone, as Claude Code does (observed on Claude Code 2.1.309; the order is undocumented and the tests pin it). A `scope: "user"` entry applies everywhere. A `scope: "project"` or `scope: "local"` entry applies only when its `projectPath` equals the clone's project identity. Claude Code appends new installs, so a user install made before a project install still wins inside the project.
- [ ] **Project identity.**
  - It is `git config ralph.projectPath`, which the clone migration saves as the host's canonical main worktree root.
  - Without that key, it is the canonical main worktree root: the parent of `git rev-parse --git-common-dir`, made absolute with `pwd -P`.
  - Layouts with a separate git dir, whose common dir is not `<root>/.git`, are rejected explicitly.
- [ ] **One identity everywhere.** The same identity applies on the host, inside the devcontainer (where the clone is mounted at `/workspace`), and in a linked or temporary worktree. Tests resolve a project-only install, with no user-scope fallback, from all three.
- [ ] **Errors.** Each of these is an error with its own message: no applicable entry, a missing `installPath`, a missing target file, the wrong registry version, and no jq. Several applicable entries are not an error: the first one wins.
- [ ] **Finding jq and the config dir.**
  - jq: on PATH first, else `git config ralph.jq`.
  - The config dir: `$CLAUDE_CONFIG_DIR`, else `git config ralph.claudeConfigDir`, else `$HOME/.claude`.
- [ ] **Tests against fake registries** cover each rule above, including paths with spaces and a real linked worktree. A cache that holds zz-fork/ralph/0.1.0/ resolves the registered version.
- [ ] **`ralph.sh` and `refine.sh`** resolve the orchestrator through the resolver. No `sort -V` over cache paths remains.
- [ ] **(host)** Scope precedence is checked against real Claude Code before this ships: a project-scope install in an isolated test clone. The result is recorded in the notes and matches the rule above, or the rule is changed.
- [ ] Checks pass.

#### US-002: Claude guards as plugin hooks behind a marker gate

**Description:** As a Ralph user, I want the Claude guard hooks to come from the plugin and act only in projects that opted in, so that a guard change ships with a plugin update.

**Acceptance Criteria:**

- [ ] **Plugin location.** These scripts live in plugins/ralph/hooks/:
  - `commit-msg-guard.sh`
  - `commit-prefix-guard.sh`
  - `master-branch-guard.sh`
  - `naming-guard.sh`
  - `notes-guard.sh`
  - `task-validator.sh`
  - `filename-length-guard.sh`
- [ ] **Wiring.** plugins/ralph/hooks/hooks.json starts with today's 13 entries and their `if:` filters. Each entry runs `"${CLAUDE_PLUGIN_ROOT}"/hooks/run.sh <guard>`. Later stories may add entries.
- [ ] **The dispatcher, run.sh.**
  - It resolves the canonical git root from `$CLAUDE_PROJECT_DIR`, and does not cross a nested repository boundary.
  - It exits 0 unless the root's .claude/ralph.json has `"pluginHooks": true`.
  - It exits 0 for a guard listed in `localGuards`.
  - Otherwise it runs the guard with the hook input unchanged, keeps the guard's exit code, and exports `RALPH_PROJECT_ROOT`.
- [ ] **Project paths.** Guards use `RALPH_PROJECT_ROOT` for project paths, and keep the payload's cwd for interpreting the command.
- [ ] **Legacy fallback.** When `RALPH_PROJECT_ROOT` is unset, as with today's direct legacy wiring, a guard computes the root itself from `$CLAUDE_PROJECT_DIR`. A test covers the guard run directly.
- [ ] **Template copies stay working.** The copies under `templates/claude/hooks/` and this repo's live `.claude/hooks/` stay byte-identical to the plugin, enforced by a parity test. A test bootstraps a project from the templates at this commit and shows that its legacy guards still block.
- [ ] **Dispatcher tests** cover:
  - the marker present and absent;
  - `localGuards`;
  - a subdirectory session;
  - a nested repository;
  - exit code 2 passing through;
  - every hooks.json entry naming an existing executable.
- [ ] Checks pass.

#### US-003: Git hook bodies in the plugin and the fixed git shim

**Description:** As a Ralph user, I want each clone's git hooks to be one fixed shim that runs the plugin's hook, so that git hook changes ship with a plugin update.

**Acceptance Criteria:**

- [ ] **Hook bodies.** The pre-commit, commit-msg and post-commit bodies live in plugins/ralph/git-hooks/.
- [ ] **The length guard.** pre-commit runs the length guard bundled in the plugin. When it runs from a legacy copy in `.git/hooks`, it falls back to `<repo>/.claude/hooks/filename-length-guard.sh`. Both layouts are tested.
- [ ] **The shim template.** templates/shims/git-hook is the same file for every hook name. It embeds the US-001 resolver and execs `<installPath>/git-hooks/<name>` with the hook's arguments.
- [ ] **Local hooks.** The local hook is `<name>.local`, in the directory `git rev-parse --git-path hooks` returns. It runs first and stops the hook if it fails, and arguments and pre-push stdin reach both hooks. A clone with `core.hooksPath` set is covered by a test.
- [ ] **When the plugin can't be resolved:**

  | Hook | Fails when | Repair message names |
  |---|---|---|
  | pre-commit, commit-msg | `ralph.pluginHooks` is true | `git commit --no-verify` |
  | pre-push | `ralph.pluginHooks` or `ralph.sharedBacklog` is true | `git push --no-verify` |
  | post-commit | never; it only warns | — |

  Otherwise the shim only warns.
- [ ] **Merge in progress.** commit-msg finds the merge message with `git rev-parse --git-path MERGE_MSG`. A test shows it recognises a merge in progress in a linked worktree.
- [ ] **Template copies.** The copies under `templates/git-hooks/` stay byte-identical to the plugin bodies, enforced by a parity test, and keep working when installed directly into `.git/hooks`.
- [ ] Checks pass.

#### US-004: Common allow rules as a user-settings fragment

**Description:** As a Ralph user, I want the common allow rules to come from one plugin fragment that lands in user settings, so that projects carry only their own extras.

**Acceptance Criteria:**

- [ ] **The fragment.** plugins/ralph/user-settings.json holds:
  - the 46 `Bash(...)` rules and `ScheduleWakeup` from today's template `settings.local.json`;
  - `attribution` with an empty commit and an empty PR trailer;
  - `sandbox` with `enabled` and `autoAllowBashIfSandboxed`.

  It holds no `Skill(...)` rules.
- [ ] **Preflight.** The `/ralph-run` preflight prints one warning listing exactly the fragment entries missing from the user's settings. It changes no file.
- [ ] **The merge helper** merges the fragment into a sample user settings file:
  - it appends missing allow entries;
  - it keeps every unrelated key and value;
  - it reports a differing value and does not overwrite it.
- [ ] **(host)** In an interactive session in a project without `Skill(...)` rules, `/ralph-status` runs with no permission prompt. The result is recorded.
- [ ] Checks pass.

#### US-005: Tracked migration with preservation

**Description:** As a Ralph user, I want a deterministic, interruption-safe migration of a project's tracked files, so that no guard is ever lost and existing settings survive.

**Acceptance Criteria:**

- [ ] **Location.** plugins/ralph/skills/ralph-init/scripts/migrate-plugin-hooks.sh, subcommand `tracked`, with an optional `--local-guards <names>`.
- [ ] **The marker comes first.** It writes the marker before anything else, so an interrupted run leaves the plugin guards enforcing.
- [ ] **Marker contents.** It merges existing marker keys rather than overwriting them, and sets `"pluginHooks": true`.
- [ ] **What it deletes.** It deletes only managed guard copies that are not in `localGuards`, and removes only their managed `settings.json` entries.
- [ ] **What it keeps.**
  - local guard files and their registrations;
  - unmanaged hook entries;
  - project-owned scripts;
  - `settings.json`, when anything is left in it.
- [ ] **`.gitignore`.** It adds `!.claude/ralph.json`.
- [ ] **Tests.**
  - A second run changes nothing.
  - Each interruption point leaves a project that still enforces its guards.
- [ ] Checks pass.

#### US-006: Clone migration and preflight states

**Description:** As a Ralph user, I want each clone migrated once, without commits and without silently dropping permissions or local hooks.

**Acceptance Criteria:**

- [ ] **Location.** The `clone` subcommand of migrate-plugin-hooks.sh. It never commits.
- [ ] **Shims.**
  - It installs the shim as pre-commit, commit-msg and post-commit, in the directory `git rev-parse --git-path hooks` returns.
  - A differing hook that `managed-file-drift.accept` lists becomes `<name>.local`.
  - An existing `<name>.local` is never overwritten: it stops with a message.
- [ ] **Switches.** It sets `ralph.pluginHooks true`. It saves `ralph.jq` and `ralph.projectPath` (the host's canonical main worktree root), plus `ralph.claudeConfigDir` when the config dir is not the default.
- [ ] **Allow rules.** It removes a fragment entry from `.claude/settings.local.json` only when user settings already contain it, and reports the entries it kept.
- [ ] **Shared backlog stays off.** It never sets `ralph.sharedBacklog`. Enabling that is explicit (US-016).
- [ ] **Preflight states.** The `/ralph-run` preflight reports each of these:
  - "not migrated";
  - "partially migrated";
  - "shims missing in this clone";
  - that plugin guards are best effort.
- [ ] **Drift check.** `managed-file-drift.sh` stops managing migrated guard copies and `settings.local.json`, and reports leftover legacy copies.
- [ ] **Tests.**
  - A second run changes nothing.
  - An existing `.local` is preserved.
  - Permissions that are not yet in user settings are kept.
- [ ] Checks pass.

#### US-007: ralph-init Init and Upgrade use the plugin

**Description:** As a Ralph user, I want new projects and upgrades to use the plugin-delivered files, so that no new project gets guard copies.

**Acceptance Criteria:**

- [ ] **Init.** It runs `migrate-plugin-hooks.sh tracked` and `clone`, and copies no guard scripts, no git hook bodies and no common allow rules.
- [ ] **Upgrade.** It runs both subcommands, and documents that a second host needs only `clone` after `git pull`.
- [ ] **Templates removed.**
  - `templates/claude/hooks/` and the hook bodies under `templates/git-hooks/` are deleted.
  - The parity tests now compare this repo's live copies with the plugin.
  - This repo keeps its legacy wiring until US-008.
- [ ] **Docs.** `SKILL.md` covers both Init and Upgrade (parity rule). The README describes the marker, the switches, the shims and the one-time migration.
- [ ] Checks pass.

#### US-008: Migrate this repo and verify on the hosts

**Description:** As the plugin's owner, I want this repo migrated with its live guards kept as local overrides, and the live behaviour checked.

**Acceptance Criteria:**

- [ ] **This repo's migration.** It is migrated with `migrate-plugin-hooks.sh tracked --local-guards <every live guard>` and `clone`.
  - The live guard copies and their registrations remain.
  - The repo's own pre-push stays a plain hook until US-017 ships the plugin's pre-push body; until then a pre-push shim could not resolve a body and would block every push.
- [ ] **(host)** **Interactive sessions.**
  - In a migrated test project, the plugin's commit-message guard blocks a bad `git commit`, including from a subdirectory session.
  - The same command is not blocked in a non-Ralph project.
- [ ] **(host)** **Devcontainer runs.** A Ralph run in the devcontainer of a migrated test project is blocked by the plugin guard, including on a first run with no plugin data dir.
- [ ] **(host)** **Plain git commits in a migrated test clone:**
  - pre-commit rejects an NFD path that duplicates an NFC tree path, and a name over 125 bytes;
  - the hooks still run with the plugin disabled in Claude;
  - with an isolated registry pointed at a removed install, the commit fails with the repair message;
  - `--no-verify` gets through.
- [ ] **(host)** **The second host.** After the plugin update and `clone`, a commit there runs the plugin's hooks.

### Shared-backlog protocol

#### US-009: Import the stage-1 shared-backlog files with a baseline harness (interactive)

**Description:** As the plugin's owner, I want the sibling project's stage-1 files in this repo unchanged, with their original tests still runnable, so that every later change is a reviewable diff against proven code.

**Acceptance Criteria:**

- [ ] **The import.** These files are copied byte-identical from commit `af5b1f8`, with sha256 sums recorded:
  - the script, as plugins/ralph/scripts/shared-backlog.sh;
  - the pre-push hook, as tests/shell/stage1/pre-push;
  - the test script, as tests/shell/stage1/shared-backlog-test.sh.
- [ ] **Baseline harness.** A pytest harness builds the stage-1 layout in a temp directory and runs the unchanged test there: `scripts/shared-backlog.sh`, `scripts/hooks/pre-push`, `scripts/tests/`. This is the immutable baseline.
- [ ] **(host)** All 75 baseline tests pass under `/bin/bash` 3.2.
- [ ] **Interactive only.** The task runs in an interactive session on the host, not in Ralph: the devcontainer cannot see the source repo.
- [ ] **Later stories.** They add regression tests for the hardened script under tests/shell/. The baseline keeps testing an unchanged copy (tests/shell/stage1/shared-backlog.sh.orig) and never the hardened script.
- [ ] Checks pass.

#### US-010: Lock primitives and command deadlines

**Description:** As a Ralph user, I want mutating protocol operations serialized per clone with real deadlines, so that two operations never interleave and none hangs forever.

**Acceptance Criteria:**

- [ ] **Two lock types, one primitive.** A reusable primitive creates atomically a protocol lock and a run lock, both directories under the canonical `git rev-parse --git-common-dir`. The owner file holds a random token, the hostname, a container flag, the pid and the start time.
- [ ] **Releasing.** An operation removes only a lock whose token is its own.
- [ ] **Stale locks.**
  - A lock is reclaimed only when its owner was on the same host and in the same pid namespace, and the pid is gone.
  - Otherwise the lock is reported, and `shared-backlog.sh unlock --force` is required.
  - Two contenders reclaiming the same stale lock do not both succeed (tested).
- [ ] **While a run lock is held:**
  - every mutating protocol command (`sync`, `claim`, `release`, `create`, `integrate`, `renumber`) refuses, unless its environment carries that run's token in `RALPH_RUN_LOCK_TOKEN`;
  - read-only commands (`check-dupes` and the pre-push validator) never take or check either lock.
- [ ] **Deadlines.**
  - Every protocol subcommand that touches the network or the clone runs under a total deadline: default 120 s, overridable through `SHARED_BACKLOG_DEADLINE`.
  - On expiry it kills its process group, reports the state, and releases only its own lock.
- [ ] **Unit tests:**
  - lock acquire and release;
  - token mismatch;
  - stale reclaim, including the race;
  - refusal while another run holds the run lock;
  - token passthrough;
  - `check-dupes` running while the protocol lock is held;
  - deadline expiry.
- [ ] **Out of scope here.**
  - The end-to-end no-deadlock push test is in US-017.
  - Wiring the run lock into the orchestrator is in US-021.
- [ ] Checks pass; **(host)** the shell suite passes under `/bin/bash` 3.2.

#### US-011: Claim rules, duplicate check and usage fix

**Description:** As a Ralph user in an opted-in project, I want claims and the duplicate check to be exact, so that the protocol neither blocks good work nor misses a duplicate.

**Acceptance Criteria:**

- [ ] **Assignees.**
  - A bare `@claude` assignee counts as unassigned.
  - A task with any other assignee besides the holder, alone or among several, is taken.
  - A claim this holder already holds is still checked for To Do status and Done dependencies.
- [ ] **Holder.** The holder comes from `--as`, else `SHARED_BACKLOG_HOLDER`, else `git config ralph.holder`. A missing holder is an error.
- [ ] **`check-dupes REV`.**
  - It reads the prefix and config from REV's tree.
  - It includes drafts.
  - It passes explicitly when REV has no `backlog/`.
  - It fails when the `backlog` executable is missing.
- [ ] **Help.** `--help` prints the whole help, exit codes included, and exits 0.
- [ ] **Tests.** Regression tests cover each rule above.
- [ ] Checks pass; **(host)** the shell suite passes under `/bin/bash` 3.2.

#### US-012: Merge-only claim and release

**Description:** As a Ralph user in an opted-in project, I want claim and release to retry without rebasing, so that no protocol path rewrites local history.

**Acceptance Criteria:**

- [ ] **Retry without rebase.** On a non-fast-forward rejection, claim and release:
  1. drop their own unpushed commit;
  2. fetch;
  3. check the claim or release again against the new origin;
  4. make a fresh commit on top;
  5. push again, at most 3 times.

  No `git rebase` remains in the script.
- [ ] **Losing a race.** A claim that loses a race reports the winner, and leaves the local master equal to origin.
- [ ] **Race tests:**
  - two clones racing to claim one task: exactly one lands;
  - a release racing a claim;
  - a retry after an unrelated commit landed on origin.
- [ ] Checks pass; **(host)** the shell suite passes under `/bin/bash` 3.2.

#### US-013: Isolated allocation in a temporary worktree

**Description:** As a Ralph user in an opted-in project, I want `create` to publish a task ID before I see it, whatever state my checkout is in.

**Acceptance Criteria:**

- [ ] **Where it runs.** `create` runs under the protocol lock in a detached temporary worktree at a freshly fetched `origin/master`.
- [ ] **What it commits.** It commits `task-N: add task` with a `Shared-Backlog-Op: <op-id>` trailer, and pushes. The operation ID, not the task ID, is fixed once per `create` and reused on every retry.
- [ ] **Plugin lookup in the worktree.** The worktree's hooks resolve the plugin with the original clone's scope (US-001), proven by a real commit made in the worktree.
- [ ] **Offline.** `create` refuses before it allocates when origin cannot be reached: exit 2, no commit and no task file.
- [ ] **Stale clones.** In clones that are behind origin, ahead of it, dirty, and on a task branch, `create` publishes an ID that is free on origin. It leaves the user's branch, index and working tree unchanged.
- [ ] **Untracked task files.** `sync` and `integrate` refuse while an untracked task file is in the working tree, and list it.
- [ ] Checks pass; **(host)** the shell suite passes under `/bin/bash` 3.2.

#### US-014: Reconciliation and recovery for create

**Description:** As a Ralph user, I want an uncertain push never to create a task twice or lose one.

**Acceptance Criteria:**

- [ ] **Lost race.** On a non-fast-forward rejection, `create` allocates again in a fresh worktree with the same operation ID, at most 3 times.
- [ ] **Uncertain push.** After a push with an uncertain outcome, it fetches and looks on origin for the operation ID.
  - If found, it reports that ID, path and SHA as the result.
  - If reconciliation itself fails, it stops without allocating again.
- [ ] **Recovery ref.** Before removing a worktree whose commit's acceptance is uncertain, it stores the commit under refs/ralph/recovery/<op-id> and prints how to finish or drop it.
- [ ] **Worktree cleanup.** Every temporary worktree is removed on every exit (success, failure, deadline or signal), after any recovery ref has been saved.
- [ ] **Tests:**
  - an ambiguous push that origin accepted is not repeated;
  - a failed reconciliation stops;
  - the recovery ref survives the worktree's removal.
- [ ] Checks pass; **(host)** the shell suite passes under `/bin/bash` 3.2.

#### US-015: integrate without automatic renumber

**Description:** As a Ralph user in an opted-in project, I want `integrate` to merge origin and publish safely, so that it never rewrites an ID that something already refers to.

**Acceptance Criteria:**

- [ ] **Merge, never rebase.** `integrate` merges `origin/master` and never rebases. Its merge commit carries an `Integrated-Origin: <sha>` trailer naming the fetched origin SHA it merged.
- [ ] **Policy fixed at the start.** Its opt-in and checks policy comes from the HEAD before the merge, fixed at invocation. Tests cover merged-in commits that change `checks`, and ones that remove the marker.
- [ ] **Fails before merging** when no checks are configured or their execution context is missing.
- [ ] **Duplicates.** On duplicate IDs it stops with an old-to-new mapping, without pushing or renumbering.
- [ ] **Interrupted runs.** An interrupted merge is preserved, not reset, and a retry first checks for a clean state.
- [ ] **Push retries.** It retries a push only on a non-fast-forward rejection, at most 3 times. It reports, and does not retry, auth failures, hook refusals and an unreachable origin.
- [ ] Checks pass; **(host)** the shell suite passes under `/bin/bash` 3.2.

#### US-016: Project shim and explicit enable or disable

**Description:** As a Ralph user, I want to opt a clone in to the protocol explicitly, and have it enforce until I explicitly turn it off.

**Acceptance Criteria:**

- [ ] **The shim.** templates/shims/shared-backlog.sh is a tracked fixed shim that embeds the US-001 resolver and execs the plugin's script.
- [ ] **Release gate.** `enable` refuses with "shared-backlog protocol not released yet" while the script's release gate is closed (FR-13). Tests open the gate with `SHARED_BACKLOG_ALLOW_UNRELEASED=1`.
- [ ] **Enable.** `shared-backlog.sh enable`:
  - requires the marker's `"sharedBacklog": true`;
  - sets `ralph.sharedBacklog true`;
  - installs the pre-push shim;
  - asks once for the host's default holder and saves `ralph.holder`.
- [ ] **Disable.** `shared-backlog.sh disable` clears `ralph.sharedBacklog`.
  - Running the clone migration again after `disable` does not turn it back on (tested).
  - A commit that removes the marker does not change the switch (tested).
- [ ] **Init and Upgrade.** They offer the opt-in, write `sharedBacklog` and an optional `checks` into the marker, and run `enable` in that clone.
- [ ] Checks pass.

#### US-017: Plugin pre-push duplicate check

**Description:** As a Ralph user in an opted-in clone, I want a push that carries a duplicate task ID refused, so that a duplicate never reaches origin.

**Acceptance Criteria:**

- [ ] **What it checks.** plugins/ralph/git-hooks/pre-push acts when `ralph.sharedBacklog` is true. It buffers stdin and runs the read-only `check-dupes` on every pushed SHA, without taking the protocol lock. It skips ref deletions.
- [ ] **What it refuses.** Tests show it refuses:
  - a tip that carries a duplicate, including one in a draft;
  - a push when `backlog` is missing.

  It passes a deletion and a push of several refs.
- [ ] **The switch decides.** It keeps enforcing after a commit that removes the marker, while the switch is on.
- [ ] **Chaining.** An existing hook keeps running as `pre-push.local` with the same stdin.
- [ ] **This repo's pre-push.** This repo's own pre-push (the version-bump guard) becomes `pre-push.local` behind the plugin's pre-push shim, and a real push of a bumped commit still runs the version-bump guard (moved here from US-008).
- [ ] **A real push.** A real `create` push through the installed shim triggers this hook while `create` holds the protocol lock. It completes without deadlock. This is tested end to end, with no stub.
- [ ] Checks pass; **(host)** the shell suite passes under `/bin/bash` 3.2.

#### US-018: Publishing lifecycle in push.py

**Description:** As a Ralph user in an opted-in project, I want each finished task published through `integrate`, and a failed publish to stop the run.

**Acceptance Criteria:**

- [ ] **When it publishes.** In an enforcing clone, the orchestrator runs `shared-backlog.sh integrate --task N`:
  - after each completed iteration that advanced master;
  - at the end of the run, unless an earlier publish failed.
- [ ] **A failed publish stops the run** before the next claim, even with `on-error=continue`. No automatic final retry follows; the run reports the failure and the local state.
- [ ] **`--no-push` in an enforcing clone.** It is allowed only with `tasks=N` naming one task:
  - the claim is still pushed;
  - the work is not published;
  - any other `--no-push` run is refused at preflight.
- [ ] **Clones that do not enforce** keep today's single end-of-run push. The report names the failure class: non-fast-forward, auth, hook or unreachable.
- [ ] **Release gate.** The shared-mode lifecycle is reachable only in a clone with `ralph.sharedBacklog` true, which `enable` cannot set while the release gate is closed. Tests open the gate explicitly.
- [ ] Checks pass.

#### US-019: Execution context and timeouts for publishing

**Description:** As a Ralph user, I want `integrate`'s checks to run where the run's tests ran, and a timeout to stop them everywhere.

**Acceptance Criteria:**

- [ ] **Where checks run.** When the run used the devcontainer, `integrate`'s configured checks run inside it through `devcontainer exec`.
- [ ] **Timeout.** The orchestrator gives the `integrate` call a total timeout. On expiry it kills the host process group and the process tree it started inside the container. A test shows no check process survives inside the container after the lock is released.
- [ ] **Interrupted merge.** After a timeout, the interrupted merge state is reported, not reset.
- [ ] Checks pass.

#### US-020: Assignee parsing and eligibility

**Description:** As a Ralph user, I want Ralph's picker to skip tasks someone else holds.

**Acceptance Criteria:**

- [ ] **Parsing.** `BacklogTask` parses `Assignee:` from `backlog task view --plain`, including several assignees.
- [ ] **Eligibility.** In every project, default mode skips To Do tasks with an assignee other than the holder. A bare `@claude` counts as unassigned.
- [ ] **Template text.** The template `CLAUDE.md` Autonomous Mode selection text states the same rule.
- [ ] Checks pass.

#### US-021: Claim lifecycle for Ralph runs

**Description:** As a Ralph user in an opted-in project, I want every Ralph run to claim a task and push the claim before working on it.

**Acceptance Criteria:**

- [ ] **Run lock.** In an enforcing clone, the orchestrator takes the US-010 run lock for the whole run. It passes `RALPH_RUN_LOCK_TOKEN` to its own protocol calls, including those inside the devcontainer.
  - A second run refuses.
  - So does an unrelated `sync` or `claim` in the same clone (tested).
- [ ] **Holder.** It is resolved once per run, and passed into the devcontainer as `SHARED_BACKLOG_HOLDER`. A missing holder refuses the run in an enforcing clone.
- [ ] **Default mode.** It syncs, picks the lowest eligible task, claims it, pushes the claim and checks it again before the iteration starts. When the claim loses, it tries the next candidate.
- [ ] **`tasks=N`.** It claims, pushes and checks again in the same way. It refuses a task another holder holds unless given `--force-claim`.
- [ ] **Already held.** A claim already held by this holder is accepted after the US-011 checks.
- [ ] **Tests:**
  - two pickers in two clones racing for one task: exactly one claim lands;
  - a missing holder;
  - several assignees;
  - a claim already held;
  - the delegated holder inside the container.
- [ ] Checks pass.

#### US-022: Guard against creating tasks during an autonomous run

**Description:** As a Ralph user in an opted-in project, I want autonomous runs to record follow-ups instead of creating tasks, so that no unpublished ID appears inside the container.

**Acceptance Criteria:**

- [ ] **The flag.** The orchestrator sets `RALPH_AUTONOMOUS=1` for every run, including inside the devcontainer.
- [ ] **The guard.** A new plugin guard, wired in hooks.json, refuses each of these when `RALPH_AUTONOMOUS=1` and the run's clone has `ralph.sharedBacklog` true:
  - `backlog task create`, including after a `cd` into another repo;
  - `shared-backlog.sh create`;
  - invoking the `ralph:ralph-handoff` skill.

  It exits 2 and tells the agent to record the follow-up in its notes.
- [ ] **Exempt from the marker gate.** This guard is not subject to the US-002 marker gate or `localGuards` (FR-4). It keys only on `RALPH_AUTONOMOUS` and the trusted `ralph.sharedBacklog` switch.
- [ ] **Best effort.** The docs and the preflight describe it as best effort, like every plugin hook, not as an absolute boundary.
- [ ] **Template text.** The template `CLAUDE.md` Autonomous Mode text says the same.
- [ ] **Tests.**
  - The guard refuses in a simulated autonomous run, including with `pluginHooks` false or absent and with the marker removed.
  - It allows the same commands interactively, and in clones that do not enforce.
- [ ] Checks pass.

#### US-023: /ralph-handoff state table

**Description:** As a Ralph user, I want a handoff to behave predictably for every combination of the destination's marker and clone switch.

**Acceptance Criteria:**

- [ ] **The state table.**

  | Destination marker `sharedBacklog` | Destination `ralph.sharedBacklog` | Behaviour |
  |---|---|---|
  | true | true | creates through the plugin's `create` and reports the ID as final only after it returns 0 |
  | true | unset or false | refuses and names the step needed (`enable`) |
  | absent or false | true | creates through the protocol (the switch is trusted) |
  | absent or false | unset or false | today's behaviour: uncommitted file, provisional ID |
- [ ] **Tests** cover the four states, and destinations that are behind origin, ahead of it, dirty, and on a task branch.
- [ ] Checks pass.

#### US-024: R-INFRA-6 with merge provenance

**Description:** As a reviewer, I want R-INFRA-6 to allow exactly the workflow's and the protocol's direct commits on master, and to check where a merge came from.

**Acceptance Criteria:**

- [ ] **What is allowed on master:**
  - the master-branch guard's allowlist paths: `.claude/`, `design/` and the editor directories;
  - `task-N: ` commits that change only `backlog/{tasks,drafts,archive,completed}/`.
- [ ] **Recording a review.** The template `CLAUDE.md` Review step, and this repo's, records the reviewed commit together with the verdict: `Review: APPROVED <sha>`, where `<sha>` is the task branch tip the reviewer saw.
- [ ] **Task-branch work** is allowed on master when:
  - for a merge, its second parent equals a SHA recorded in an APPROVED note of the task it names, and its tree equals `git merge-tree` of its parents;
  - for a fast-forward landing, every landed commit is equal to, or an ancestor of, such a recorded SHA.
  
  No branch ref needs to survive. A verdict recorded for an earlier SHA does not approve commits made after it.
- [ ] **Integration merges** are allowed when:
  - their `Integrated-Origin: <sha>` trailer, written by `integrate`, names the fetched origin SHA they used;
  - the second parent equals that SHA, and the SHA is reachable from origin's base branch;
  - the tree equals `git merge-tree` of the parents.
- [ ] **Hand-resolved merges.** A merge whose tree differs is allowed only through the review route: TASK-N's notes record `Integration review: APPROVED <merge-sha>` for exactly that merge.
- [ ] **Fixtures.**

  | Approved | Flagged |
  |---|---|
  | a `design/` commit | a clean merge from an unreviewed task branch |
  | a `task-N:` task-file commit | a clean merge from an arbitrary side branch |
  | a reviewed merge whose task branch was deleted | a merge whose second parent is newer than the recorded APPROVED SHA (stale verdict) |
  | a reviewed fast-forward landing | a hand-edited merge with no integration review |
  | a clean integration merge with its trailer | |
  | a hand-resolved merge with a recorded integration review | |
- [ ] Checks pass.

#### US-025: Release tag validation (this repo only)

**Description:** As the plugin's owner, I want each version tag checked against its release commit, so that two hosts bumping to the same version are caught.

**Acceptance Criteria:**

- [ ] **The rule.** The release commit of vX.Y.Z is the first commit, along origin's base branch's first-parent history, where both manifests read X.Y.Z. The tag, peeled for annotated tags, must point at that commit.
- [ ] **The check at pre-push.** `version-bump-guard.sh` looks up origin's tag with `git ls-remote origin 'refs/tags/vX.Y.Z' 'refs/tags/vX.Y.Z^{}'`, compares the peeled commit, and runs under a network deadline. It refuses when:
  - the tag exists there with a different peeled commit;
  - the two manifests disagree on the pushed tip.

  It refuses with a clear message when origin cannot be reached. Commits after the release with the same version pass.
- [ ] **Docs.** The repo's release procedure in `.claude/` documents the manual re-bump after a version conflict. An existing tag is never moved.
- [ ] **Tests.** Fixtures cover:
  - both sides tagging the same version;
  - a normal bump;
  - a commit after the release;
  - an annotated tag;
  - an unreachable origin;
  - two divergent same-version bumps merged together.
- [ ] Checks pass.

#### US-026: Release the shared-backlog protocol

**Description:** As the plugin's owner, I want the protocol switched on for users only once all of its parts are in place, so that no intermediate commit exposes half of it.

**Acceptance Criteria:**

- [ ] **Open the gate.** The release gate in plugins/ralph/scripts/shared-backlog.sh is opened (FR-13), after US-014, US-017, US-019, US-021, US-022 and US-023 are Done.
- [ ] **No override in production.** `enable` works without `SHARED_BACKLOG_ALLOW_UNRELEASED`, and no production path sets that variable (checked by grep).
- [ ] **Docs.** The README and the ralph-init docs describe the protocol: opt-in, `enable` and `disable`, and the commands.
- [ ] **(host)** End to end in a test project, on two clones of one test origin:
  - enable;
  - two racing `create`s;
  - two racing default-mode Ralph claims;
  - one `integrate`.
  
  No duplicate ID and no double claim results.
- [ ] Checks pass.

## 5. Functional Requirements

- **FR-1: The marker.** The ownership marker is a tracked `.claude/ralph.json` with these optional keys:

  | Key | Type |
  |---|---|
  | `pluginHooks` | bool |
  | `localGuards` | array of guard names |
  | `sharedBacklog` | bool |
  | `checks` | string |

  `.gitignore` carries `!.claude/ralph.json`. The marker declares intent; it is not what enforces.
- **FR-2: Clone-local git config.**
  - **Keys:** `ralph.jq`, `ralph.claudeConfigDir`, `ralph.projectPath`, `ralph.pluginHooks`, `ralph.sharedBacklog` and `ralph.holder`.
  - **The trusted switches** are `ralph.pluginHooks` and `ralph.sharedBacklog`.
  - **Who sets them:** only the migration, `shared-backlog.sh enable` and `disable`, and the user. Nothing rewrites them to switch identity.
- **FR-3: Finding the plugin.** The plugin is resolved only by the US-001 resolver, which uses the main worktree's root for scope. It takes the first registry entry that applies (user scope, or project or local scope for this project), the rule Claude Code 2.1.309 was observed to follow, so the shims and the Claude hooks run the same install. Nothing selects a plugin by scanning the cache.
- **FR-4: Claude hooks.** The plugin's guard hooks act only when the marker at the session's canonical git root has `"pluginHooks": true`, and only for guards not in `localGuards`. The one exception is the autonomous-creation guard (US-022), which keys only on `RALPH_AUTONOMOUS` and `ralph.sharedBacklog`.
- **FR-5: Blocking when the plugin is missing.** pre-commit and commit-msg block on `ralph.pluginHooks`, and pre-push on `ralph.pluginHooks` or `ralph.sharedBacklog`. post-commit only warns. `--no-verify` is the documented bypass.
- **FR-6: The holder.** It comes from `--as`, else `SHARED_BACKLOG_HOLDER`, else `ralph.holder`, and is resolved once per run. A bare `@claude` assignee counts as unassigned everywhere.
- **FR-7: Locks.**
  - The protocol lock serializes mutating protocol operations per clone, and the run lock allows one Ralph run per clone.
  - Read-only validation takes no lock.
  - Locks use ownership tokens, and only the owner releases one.
- **FR-8: Publishing a task ID.** In an opted-in project, a task ID becomes visible only after `create` has pushed it. `create` refuses when origin cannot be reached, and never repeats an allocation after an uncertain push.
- **FR-9: No automatic renumber.** No automatic path renumbers or rebases. Renumbering is a manual command only.
- **FR-10: Exit codes.**

  | Code | Meaning |
  |---|---|
  | 0 | ok |
  | 1 | refused, conflict or check failed |
  | 2 | origin unreachable |
  | 64 | usage error |
- **FR-11: Deadlines.** Every protocol subcommand runs under a total deadline. A timeout preserves state, and releases only the caller's own lock.
- **FR-12: Portability.** All shell code passes the bash 3.2 static guard and is portable between GNU and BSD tools (R-INFRA-3).
- **FR-13: The release gate.** `shared-backlog.sh` carries a release gate that stays closed until US-026. While it is closed, `enable` refuses, so no clone can switch on the shared-mode paths: claim lifecycle, publishing, the no-create guard and protocol handoffs. Tests open it with `SHARED_BACKLOG_ALLOW_UNRELEASED=1`.

## 6. Non-Goals

- `.devcontainer/`, `CLAUDE.md` and `.claude/brainstorm-rules.md` stay per project.
- No automatic shim install, and no batch migration across projects.
- No SessionStart pointer file for finding the plugin.
- No Codex session support.
- No per-host ID ranges or prefixes, and no `backlog doctor --fix`.
- No automatic renumber, no rebase in the protocol, no task creation inside autonomous runs, and no provisional IDs offline.

## 7. Technical Considerations

- **Plugin hooks are best effort.** A plugin hook that cannot start does not block. The git hooks are the hard backstop.
- **Paths inside the devcontainer.** The devcontainer binds `~/.claude` at the host path, and `CLAUDE_CONFIG_DIR` points there, so registry paths resolve in both places. `.git/config` is shared through the workspace bind mount, so the clone switches apply in both.
- **jq.** It is a requirement for the git hook shims, as it already is for the guards.
- **Dependencies (story → stories it needs):**

  | Story | Needs |
  |---|---|
  | US-003 | US-001 |
  | US-005 | US-002, US-003, US-004 |
  | US-006 | US-005 |
  | US-007 | US-006 |
  | US-008 | US-007 |
  | US-010 | US-009 |
  | US-011 | US-010 |
  | US-012 | US-011 |
  | US-013 | US-003, US-012 |
  | US-014 | US-013 |
  | US-015 | US-010, US-011 |
  | US-016 | US-001, US-006, US-010 |
  | US-017 | US-003, US-011, US-013, US-014, US-016 |
  | US-018 | US-015, US-017 |
  | US-019 | US-018 |
  | US-021 | US-012, US-016, US-018, US-020 |
  | US-022 | US-002, US-016 |
  | US-023 | US-014, US-016 |
  | US-024 | US-015 |
  | US-026 | US-014, US-017, US-019, US-021, US-022, US-023 |

  US-001, US-002, US-004, US-009, US-020 and US-025 have no dependencies. US-026 opens the release gate, so intermediate commits never expose shared mode to users.

## 8. Success Metrics

- **No per-project runs.** A plugin release that changes a guard or a git hook reaches every migrated project on a host with no per-project run.
- **No leftovers from migration.** The per-clone migration never commits, is idempotent, and leaves guards enforcing at every interruption point.
- **No duplicates.** No duplicate task ID reaches origin in an opted-in project.
- **No double work.** No two hosts work the same task in an opted-in project.

## 9. Open Questions

- **Scope precedence** in the real registry, checked on the host in US-001 before the resolver ships. Answered on Claude Code 2.1.309: the first applicable entry in registry order wins.
- **`CLAUDE_PROJECT_DIR`** when a session starts in a subdirectory, covered by US-002's tests and US-008's host check.
- **Dropping the `Skill(...)` allow rules,** checked on the host in US-004.
