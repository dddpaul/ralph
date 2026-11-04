---
export: true
title: Plugin-Delivered Project Files (Claude guards, git hooks, allow rules)
type: design
---

# Plugin-Delivered Project Files (Claude guards, git hooks, allow rules)

## Architecture decision

Today ralph-init copies its managed files into every project, and `ralph-init upgrade` refreshes them. With two hosts (one clone of each project per host, one origin), that costs three things:

- **Rerun on the second host:** git hooks and `.claude/settings.local.json` live outside git. So each clone on each host needs its own upgrade.
- **Projects × hosts:** every Ralph project needs an upgrade run after every plugin release that touches a template. That is dozens of projects on one host and a handful also cloned on the second.
- **Diverging upgrades:** upgrading the same project on both hosts makes two different commits of the same files, and those conflict.

**Chosen: approach A — the plugin carries the content, and projects keep only fixed shims and a marker.**

- The Claude guard hooks move into the plugin's own `hooks/hooks.json`.
- The git hooks become one fixed shim per clone, which runs the plugin's hook of the same name.
- The common allow rules move to user settings.
- After one migration per project, a plugin release reaches every migrated project on a host through the plugin update alone.

Rejected alternatives:

- **B: tracked `.githooks/` plus `core.hooksPath`.** It still needs one upgrade per project per template change, and the copies still drift.
- **C: a batch upgrader that writes into every project.** It automates the copying instead of removing it, writes into running Ralph trees, and cannot handle accepted deviations.

Template changes since 2026-08-01, by area:

| Area | Changes | Under A |
|---|---|---|
| `.devcontainer/` | 19 | stays per project |
| Claude guard hooks | 9 | plugin |
| git hooks | 5 | plugin, behind shims |
| `CLAUDE.md` | 3 | stays per project |
| `settings.local.json` | 1 | user settings |

### Evidence (Claude Code 2.1.309, macOS host, probe plugin loaded with `--plugin-dir`)

- **Plugin hooks run under Ralph's exact flags** (`claude --dangerously-skip-permissions --print`):
  - The plugin's `hooks/hooks.json` SessionStart and PreToolUse hooks both ran.
  - `if: Bash(...)` filters work in a plugin's `hooks.json`.
  - Exit 2 blocks the tool call.
  - The hook process gets `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA` and `CLAUDE_PROJECT_DIR`.
- **A plugin hook that cannot start does not block.** In a sandboxed nested run the hook could not create its data dir and failed with status 1. The command it should have blocked ran. Plugin guards are therefore best effort.
- **SessionStart `additionalContext` loads in `-p`, up to a size limit.** At 8.0k characters it arrived whole. At 14.8k, only a 2 KB preview reached the model.
- **An external `@`-import in `CLAUDE.md` does not load in `-p` without prior approval.** The approval flag (`hasClaudeMdExternalIncludesApproved`) lives in the host's `~/.claude.json`. The container uses `$CLAUDE_CONFIG_DIR/.claude.json` instead, so an approval given on the host does not carry over.
- **A plugin skill needed no `Skill(...)` allow rule** in `-p` under the default permission mode. That covers this mode only; the interactive mode is still to be confirmed.
- **The registry of installed plugins** is `<config>/plugins/installed_plugins.json`, `"version": 2`. `plugins["ralph@dddpaul-ralph"]` is a list of `{scope, version, installPath, projectPath}`.
- **Cache order is not install order.** Old plugin versions stay in `<config>/plugins/cache/`. A `sort -V` over whole cache paths ranks the marketplace name above the version, so `.../zz-fork/ralph/0.1.0/` sorts after `.../dddpaul-ralph/ralph/0.14.15/`.

## Components / flows

- **Ownership marker.**
  - A tracked `.claude/ralph.json` (proposed name), for example `{"pluginHooks": true, "localGuards": []}`. It gets a `!.claude/ralph.json` exception in `.gitignore`.
  - Without the marker, the plugin's guards do nothing and the project's legacy wiring stays in charge.
  - With the marker, the plugin owns every managed guard. A project override must be listed explicitly in `localGuards`.
  - Because the marker is tracked, both hosts agree about a project.
- **Claude guard hooks in the plugin.**
  - The guard scripts, `task-validator.sh` and `filename-length-guard.sh` move from `templates/claude/hooks/` to `plugins/ralph/hooks/`.
  - `plugins/ralph/hooks/hooks.json` carries today's 13 entries with the same `if:` filters. Every entry calls one dispatcher with the guard's name.
- **Dispatcher (`plugins/ralph/hooks/run.sh <guard>`):**
  - It resolves the canonical git root from `$CLAUDE_PROJECT_DIR` and never walks past a nested repository boundary.
  - It exits 0 unless the marker is at that root. It also exits 0 if the guard is listed in `localGuards`.
  - Otherwise it runs the guard with the hook input unchanged and keeps the guard's exit code. It exports the resolved root as `RALPH_PROJECT_ROOT`.
  - Guards keep the payload's cwd for interpreting the command and use `RALPH_PROJECT_ROOT` for project paths.
- **Git hooks in the plugin.**
  - The bodies of pre-commit, commit-msg and post-commit move to `plugins/ralph/git-hooks/`; pre-push is added later.
  - pre-commit runs the plugin's bundled `filename-length-guard.sh`, not a project copy.
- **The git shim, identical for every hook name and never changed after install.** It resolves the installed plugin as follows:
  1. **Find `jq`:** first on `PATH` (this covers the container), else the absolute path saved in `git config ralph.jq`.
  2. **Find the config dir:** `$CLAUDE_CONFIG_DIR`, else `git config ralph.claudeConfigDir`, else `$HOME/.claude`.
  3. **Read the registry:** `installed_plugins.json`, checking that its `version` is 2. Take only `ralph@dddpaul-ralph`.
  4. **Pick the entry:** a project-scope entry whose `projectPath` is this clone's canonical git root wins over the user-scope entry. More than one candidate, or a missing `installPath`, is an error.
     *Superseded (TASK-321): the host check on Claude Code 2.1.309 showed Claude Code takes the first applicable entry in registry order; the PRD's US-001 holds the rule now.*
  5. **Run the hook:** `exec` the file `<installPath>/git-hooks/<name>`.
  - **Before the plugin's hook:** if `.git/hooks/<name>.local` exists, the shim runs it first and stops if it fails. Arguments pass through to both, and pre-push stdin is read once and given to each.
  - **Independent of Claude:** git enforcement depends only on the marker and the installed package, not on `enabledPlugins` in Claude's settings.
- **What happens when lookup fails:**

  | Situation | pre-commit / commit-msg / pre-push | post-commit |
  |---|---|---|
  | Marker present; `jq`, registry, entry or body missing, or ambiguous entries | Exit 1 with a repair message (install the plugin, run `ralph-init upgrade`, bypass with `git commit --no-verify`) | Warns and exits 0 |
  | Marker absent | Best effort: run the body if found, else warn | Same |

- **`ralph.sh` and `refine.sh`** switch from scanning the cache to the same registry lookup.
- **Settings fragment `plugins/ralph/user-settings.json`.** It holds:
  - the 46 `Bash(...)` rules plus `ScheduleWakeup` (47 allow rules);
  - `attribution` with an empty commit and PR trailer;
  - `sandbox` with `enabled` and `autoAllowBashIfSandboxed`.

  How it reaches each host:
  - **Second host:** configuration management merges it from the installed plugin's `installPath`.
  - **Primary host:** the `/ralph-run` preflight lists the entries missing from `~/.claude/settings.json`, and the owner adds them.
  - **Merge rules:** a merge appends missing allow entries and never overwrites an existing value. A differing value is reported, not changed.
- **Migration script** (called by Upgrade; deterministic and testable).
  - **Tracked part,** done once per project on one host, then committed and pushed:
    - delete the guard copies under `.claude/hooks/`, keeping project-own scripts;
    - remove the 13 hook entries from `.claude/settings.json`, deleting the file if it is left empty;
    - write the marker and its `.gitignore` exception.
  - **Per-clone part,** once per host; on the second host, run after `git pull`:
    - install the shims for pre-commit, commit-msg and post-commit;
    - save `ralph.jq` and, if it is not the default, `ralph.claudeConfigDir`;
    - turn a git hook that differs from the template and is listed in `managed-file-drift.accept` into `<name>.local`;
    - remove the common entries from `.claude/settings.local.json`.
  - **No commit in the per-clone part,** so the two hosts cannot make diverging commits.
  - **A second run changes nothing.**
- **Preflight and drift check.**
  - **Project states:** the preflight reports "not migrated", "partially migrated" (marker plus legacy `settings.json` entries, or no marker plus missing guard copies) and "shims missing in this clone".
  - **Best effort:** the preflight and the migration say that plugin guards are best effort.
  - **Drift check:** it stops managing `settings.local.json` and the guard copies, and starts reporting a leftover legacy copy.
- **Rollout and rollback.**
  - **Order:** release the plugin first. Unmigrated projects are unaffected.
  - **Lazy migration:** each project migrates when it is next worked on.
  - **Rollback:** remove the marker, or install the previous plugin version. Either is honoured, because shims read the registry.
- **This repo.**
  - **Live copies:** the repo keeps its live guard copies and lists them in `localGuards` for testing its own changes.
  - **Template parity:** the parity tests compare those copies with `plugins/ralph/hooks/`.
- **Init.** New projects get the marker and shims, and no guard copies.

## Scope cuts

- **`.devcontainer/` stays per project.** The devcontainer CLI reads it from the repo. It is the largest source of upgrades (19 changes since August), but it is tracked, so only one upgrade per project is needed and the other host pulls it.
- **`CLAUDE.md` and `.claude/brainstorm-rules.md` stay per project, as today.** They are tracked and changed 3 times since August. The carriers that were considered each failed:
  - an external `@`-import does not load in `-p`;
  - user rules would load in every project;
  - SessionStart text has a size limit, and the two generic parts total about 15k characters.
- **No automatic shim install.** For example, a SessionStart hook writing into `.git/hooks`. The preflight reports missing shims instead.
- **No batch migration across projects.**
- **No SessionStart pointer file for plugin lookup.** It would resolve at session time rather than at commit time, so after a rollback, uninstall, disabled plugin or scoped session it can point at a stale cached body that still exists.
- **Codex sessions are out of scope.**
- **The `commit-msg` `.git/MERGE_MSG` check, which is wrong in linked worktrees, is a separate defect.** It predates this design and gets its own task.

## Open questions

- **Scope precedence in the real registry:** whether a project-scope install wins over the user-scope one. Verify against Claude Code with a project-scope install. *Answered in the PRD's US-001: the first applicable entry in registry order wins.*
- **`CLAUDE_PROJECT_DIR` when a session starts in a subdirectory:** whether it is the launch directory or the git root. Verify.
- **The 7 `Skill(...)` rules:** whether an interactive session prompts without them. Drop them only after an interactive check.
- **The marker's final file name and schema** (`.claude/ralph.json` is a proposal).
- **The planned shared-backlog pre-push shim** handed off from a sibling project should become this same shim mechanism, not a second one.
- **A future change to the registry schema by Claude Code** makes every shim fail closed with the repair message. The repair is a shim refresh per clone. That is accepted as rare.

## Hand-off

Next: `ralph-prd` to formalize as PRD, then `ralph-backlog` to generate tasks. The work spans several tasks with shared contracts (the marker, the plugin lookup, the dispatcher gate), so it detours through a PRD.

## Distilled for ralph-task

**Direction:** Approach A — the ralph plugin carries the Claude guard hooks, the git hook bodies and the common allow rules. Each project keeps a tracked ownership marker, and each clone keeps fixed git hook shims that resolve the installed plugin from Claude Code's plugin registry.

**Locked decisions (with rationale):**

- **Plugin `hooks/hooks.json` with one dispatcher.** The 13 guard entries keep their `if:` filters and call `plugins/ralph/hooks/run.sh <guard>`. *Rationale:* tested under `claude --dangerously-skip-permissions --print`: plugin hooks fire, `if:` works, and exit 2 blocks.
- **The gate is the tracked marker at the canonical git root of `$CLAUDE_PROJECT_DIR`.** The marker is `.claude/ralph.json` (proposed name) with `pluginHooks` and `localGuards`. Without the marker the plugin does nothing. With it, the plugin owns every guard not listed in `localGuards`. *Rationale:* file-existence checks fail on half-migrated projects, and a tracked marker makes both hosts agree.
- **The dispatcher exports `RALPH_PROJECT_ROOT`.** Guards use it for project paths and keep the payload cwd for command interpretation. *Rationale:* sessions started in a subdirectory must keep their guards, and the guards today mix project-dir and ambient-cwd resolution.
- **The git hooks are fixed shims that read `installed_plugins.json` with `jq`.**
  - `jq` is taken from PATH, else from the saved `git config ralph.jq`.
  - The config dir is `$CLAUDE_CONFIG_DIR`, else `git config ralph.claudeConfigDir`, else `$HOME/.claude`.
  - The registry `version` must be 2, and only `ralph@dddpaul-ralph` counts. A project-scope entry for this git root beats the user scope. Ambiguity or a missing `installPath` is an error.
  - The shim runs `<installPath>/git-hooks/<name>`.
  
  *Rationale:* cache-directory sorting picks the wrong plugin, and a GUI git client may lack `jq` on PATH.
- **Fail closed when the marker is present.** pre-commit, commit-msg and pre-push exit 1 with a repair message naming `git commit --no-verify` as the bypass. post-commit warns. *Rationale:* owner decision; both hosts run Claude Code, and `--no-verify` is git's documented bypass.
- **`.git/hooks/<name>.local` runs before the plugin body and stops the hook on failure,** with arguments and pre-push stdin passed to both. *Rationale:* it keeps project-own hooks and accepted deviations.
- **Git enforcement ignores Claude's `enabledPlugins`.** *Rationale:* the clone's marker is the opt-in.
- **`ralph.sh` and `refine.sh` use the same registry lookup.** *Rationale:* they share the cache-sorting defect.
- **The plugin pre-commit runs its own bundled `filename-length-guard.sh`.** *Rationale:* today it runs only the project copy, so deleting the copies would silently drop the 125-byte check.
- **Common allow rules go to user settings from `plugins/ralph/user-settings.json`.** The fragment holds 46 Bash rules, `ScheduleWakeup`, `attribution` and `sandbox`. A merge never overwrites existing values. *Rationale:* a plugin cannot ship allow rules, and the owner accepts the rules applying in every project.
- **Migration is a script called by Upgrade, run lazily per project.** Its tracked part is committed once on one host. Its per-clone part never commits. *Rationale:* it is testable and idempotent, and it avoids diverging commits.

**Scope cuts:**

- `.devcontainer/` is not moved.
- `CLAUDE.md` and `.claude/brainstorm-rules.md` stay per project.
- No automatic shim install.
- No batch migration.
- No SessionStart pointer file.
- No Codex support.
- The `.git/MERGE_MSG` worktree fix is a separate task.

**Acceptance criteria (sketch):**

- **Dispatcher tests.**
  - Without the marker it exits 0, and with it it runs the guard.
  - It exits 0 for a guard listed in `localGuards`.
  - It keeps exit code 2 and passes the hook input unchanged.
  - It exports `RALPH_PROJECT_ROOT`, resolves the root from a subdirectory, and does not cross a nested repo.
- **`hooks.json` test:** 13 entries with their `if:` filters; every referenced script exists and is executable.
- **Shim lookup tests,** against fake registries:
  - project scope beats user scope;
  - ambiguous entries, a missing `installPath` and the wrong `version` are each an error;
  - `jq` from PATH and from `ralph.jq`; the config dir from `ralph.claudeConfigDir`;
  - paths with spaces.
- **Shim behaviour tests.**
  - With the marker and the plugin missing, pre-commit and commit-msg exit 1 with the repair message, and post-commit exits 0 with a warning.
  - `.local` runs first and its failure stops the hook.
  - pre-push stdin reaches both hooks.
  - The bash 3.2 static guard passes.
- **Plugin pre-commit tests:** it rejects a non-NFC filename and a filename over 125 bytes with no project `.claude/hooks/` present.
- **Settings fragment tests.**
  - It holds the 47 rules and no `Skill(...)` rules.
  - A merge into a sample user settings file keeps unrelated keys and values.
  - The preflight lists exactly the missing entries.
- **Migration script tests.**
  - It deletes the guard copies, keeps project-own scripts and strips the 13 `settings.json` entries.
  - It writes the marker and its `.gitignore` exception.
  - It installs the shims and saves `ralph.jq`.
  - It moves an accepted hook to `.local` and trims `settings.local.json`.
  - A second run changes nothing.
  - The preflight flags a partially migrated project.
- **Live checks (installed plugin, recorded in task notes).**
  - **Interactive guards:** a guard blocks in a migrated project, including a session started in a subdirectory, and not in a non-Ralph project.
  - **Skill rules:** `/ralph-status` runs without a permission prompt.
  - **Devcontainer:** a Ralph run in the devcontainer is blocked by the plugin guard, including on a first run with no plugin data dir.
  - **Plain `git commit` in a migrated clone:**
    - it runs the plugin's hooks with the plugin disabled in Claude;
    - it fails with the repair message when the registry points at a removed install;
    - it passes with `--no-verify`.
  - **Second host:** after the plugin update and the per-clone step, it commits through the plugin's hooks.
  - **Scope precedence:** project-scope versus user-scope precedence is recorded from real Claude Code.

**Implementation checklist:**

1. **Plugin lookup.** Add the shared registry lookup (jq, config dir, scope precedence, error cases) and switch `ralph.sh` and `refine.sh` to it, with tests.
2. **Guards and dispatcher.** Move the guards, `task-validator.sh` and `filename-length-guard.sh` to `plugins/ralph/hooks/`. Add `hooks.json` and the `run.sh` dispatcher with the marker gate, `localGuards` and `RALPH_PROJECT_ROOT`. Update the guards that resolve project paths; repoint the bats tests.
3. **Git hooks and shim.** Move the git hook bodies to `plugins/ralph/git-hooks/`, with pre-commit using the bundled length guard. Add the fixed shim template with `.local` chaining and fail-closed behaviour; add tests.
4. **Settings fragment.** Add `plugins/ralph/user-settings.json` and the preflight check of user settings, with merge-preservation tests. Drop the `Skill(...)` rules after the interactive check.
5. **Migration and ralph-init.** Add the migration script. Change ralph-init Init (marker and shims, no guard copies) and Upgrade (call the script) together. Update `managed-file-drift.sh` and the preflight states.
6. **This repo.** Migrate this repo: marker with `localGuards` for its live copies; template parity against `plugins/ralph/hooks/`.
7. **Docs and live checks.** Update the README and ralph-init docs, then run the live checks on both hosts.
8. **Separate task:** fix `commit-msg`'s `.git/MERGE_MSG` test for linked worktrees, using `git rev-parse --git-path MERGE_MSG`.

---

## Addendum: shared-backlog protocol (added 2026-11-04)

### Why

**Task IDs collided between two clones of one origin, in opposite directions.**

- One destination clone was behind origin and allocated an ID that upstream already had.
- Another clone was ahead: it allocated an ID locally, and the other host then took the same number.

**A duplicate ID is costly and hard to see.** It blocks every ID-based backlog command until it is repaired. It also arrives with no git conflict, because the two file names differ.

**Two obvious fixes don't work.**

- Per-host ID ranges or prefixes are rejected: backlog.md has one project-wide prefix and always allocates max+1.
- `backlog doctor --fix` is not a repair: when tested, it renumbered the copy that was already on origin.

**A sibling project has already proven a fix.** Its stage-1 implementation is pinned at commit `af5b1f8`. It is one bash 3.2 script with 75 tests, plus a pre-push duplicate check. The script treats an ID as provisional until its push lands, and lets the push to origin decide which host holds a task. This addendum moves that protocol into the plugin, hardened after review.

**Picking a task is not claiming it.** Two hosts that both filter out assigned tasks still pick the same unassigned task, because neither has pushed a claim yet.

### What changed

**Owner decisions (2026-11-04):**

1. **The protocol is opt-in per project.** The tracked marker declares it with `"sharedBacklog": true`. The per-clone migration then turns on a clone-level switch, `git config ralph.sharedBacklog true`, and the hooks enforce on that switch. Turning enforcement off takes an explicit command. A commit that drops the marker does not turn it off.
2. **`/ralph-handoff` uses the protocol only when the destination opted in.** In that case it creates the task through the protocol. Otherwise it keeps today's behaviour: the task file stays uncommitted and the ID is reported as provisional.
3. **A bare `@claude` assignee counts as unassigned,** in both `claim` and Ralph's task picker. No task files are rewritten.
4. **An autonomous run in an opted-in project creates no tasks.** It records follow-ups in its task's notes. A guard enforces this.
5. **Opted-in runs publish after each completed iteration,** so the next claim starts from a master that matches origin.
6. **`create` refuses when origin is unreachable,** instead of handing out a provisional ID.

**What changes in the ralph code:**

| Area | Change |
|---|---|
| Script | `plugins/ralph/scripts/shared-backlog.sh`, ported from `af5b1f8`, with a tracked fixed project shim that resolves the plugin through the registry resolver |
| `create` | Allocates in a detached temporary worktree, under a protocol lock |
| `integrate` | Never renumbers; checks run in the run's context |
| Duplicate check | Reads its settings from the revision it inspects |
| pre-push | A plugin body enforced by the clone switch |
| `push.py` | Publishes through `integrate` after each iteration |
| Picker | Claims a task before starting it |
| Guard | Refuses task creation inside an autonomous run |
| `/ralph-handoff` | Creates through the protocol in opted-in destinations |
| R-INFRA-6 | Allows only the protocol's commits and reviewed or integration merges on master |
| `commit-msg` | Fixes the `MERGE_MSG` check for worktrees |
| This repo | Its release process handles version-tag clashes |

### Implementation checklist

Item 1 is interactive; items 2 to 11 depend on it and on the base design's resolver and migration work. The Distilled block below has the full steps.

1. Import the stage-1 files from `af5b1f8` unchanged.
2. Harden the script.
3. Add the project shim and the clone switch.
4. Add the plugin pre-push body.
5. Make `push.py` publish through `integrate` after each iteration.
6. Make the picker claim before it starts a task.
7. Add the guard against creating tasks during a run.
8. Make `/ralph-handoff` create through the protocol.
9. Rewrite R-INFRA-6.
10. Fix the `MERGE_MSG` check in `commit-msg`.
11. Add tag-to-content release validation in this repo.

### Distilled for ralph-task

**Direction:** Move the shared-backlog protocol into the ralph plugin. It is opt-in per project: the tracked marker declares it and a clone-level switch enforces it. It reuses the base design's registry resolver, marker and shim mechanism. The push to origin decides which task IDs and claims are real.

**Locked decisions (with rationale):**

- **The script lives in the plugin.** `plugins/ralph/scripts/shared-backlog.sh`, ported from the stage-1 implementation at `af5b1f8` together with its tests.
  - It keeps the subcommands `sync`, `claim`, `release`, `create`, `integrate`, `check-dupes` and `renumber`, and drops `install-hooks`.
  - Opted-in projects keep a tracked fixed shim, `scripts/shared-backlog.sh`, which resolves the plugin through the registry resolver.
  - The port fixes `usage()`: today `--help` stops at the `# Exit codes` line and exits 64.

  *Rationale:* one implementation for every project, proven by the stage-1 tests.
- **Configuration has three layers.**
  - **The marker.** `.claude/ralph.json` holds `"sharedBacklog": true` and an optional `"checks"`: a command run with `sh -c` at the repo root, which maps onto the script's existing `SHARED_BACKLOG_CHECKS`.
  - **The clone switch.** The per-clone migration sets `git config ralph.sharedBacklog true` from the marker. An explicit `shared-backlog.sh disable` clears it.
  - **The holder.** It comes from `--as`, then `SHARED_BACKLOG_HOLDER`, then `git config ralph.holder`, which the migration sets as the host default.

  *Rationale:* the holder differs per agent per host, so it cannot be tracked. Enforcement must not switch off through an ordinary commit.
- **Holder delegation.** A run launched by a holder acts as that holder. The launcher passes `SHARED_BACKLOG_HOLDER` into the run, including into the devcontainer for that run. A separately dispatched worker uses its own holder and claims for itself. Shared git config is never rewritten to switch identity. *Rationale:* a separate run identity would make the launcher's own claim look like someone else's.
- **One protocol lock.** A single lock in the git common dir covers every protocol operation and a run's claim and publish steps. One protocol operation runs per clone at a time. The design states that a person's own git commands in the same clone during an operation are unsupported. *Rationale:* claims and creates must not interleave.
- **`create` allocates in a detached temporary worktree.**
  - **Steps.**
    1. Make the worktree at a freshly fetched `origin/master`.
    2. Run `backlog task create` there.
    3. Commit `task-N: add task` with a `Shared-Backlog-Op: <id>` trailer.
    4. Push.
  - **A lost race.** On a non-fast-forward rejection, it fetches again and retries in a fresh worktree, at most 3 times.
  - **An uncertain push.** If the push outcome is unclear, it checks origin for the operation's trailer before retrying.
  - **Cleanup.** It removes the worktree on every exit, and keeps recovery details when acceptance is uncertain.
  - **What it leaves alone.** It never touches the user's index, working tree or branch. Only the remote-tracking refs move.
  - **Offline.** It refuses, with exit 2.
  - **The result.** The ID is final when `create` returns 0. The user's clone picks the task up on its next `sync` or `integrate`.
  - **Untracked task files** in the user's tree are flagged, and `sync` and `integrate` refuse to run until they are dealt with.

  *Rationale:* destinations that are ahead, dirty or on a task branch all work, and an ID is never exposed before it is published.
- **Claims and assignees.**
  - A bare `@claude` assignee counts as unassigned.
  - A task is taken if it has any other assignee besides the holder, alone or alongside others.
  - A claim this holder already has is still rechecked: status To Do and dependencies Done.

  *Rationale:* existing tasks carry the generic `@claude`, which names no host.
- **The picker claims before starting, in opted-in projects.**
  - Default-mode Ralph syncs, picks the lowest eligible To Do task, claims it and pushes the claim, then checks it again before the iteration starts.
  - When a claim loses, it moves to the next candidate.
  - `tasks=N` refuses a task held by another holder unless forced.
  - `BacklogTask` parses `Assignee:`. In every project, the picker skips tasks with a real assignee other than the holder.

  *Rationale:* picking is not claiming.
- **Opted-in runs publish through `integrate` after each completed iteration.** `push.py` calls `integrate` with a real total timeout that kills the whole process tree. It retries only when the push was rejected as non-fast-forward. Network, auth and hook failures are reported, not retried. Projects that haven't opted in keep today's single push, with the failure class now reported. *Rationale:* the next claim needs a master that matches origin.
- **`integrate` never renumbers on its own.**
  - **Merge.** It merges `origin/master` and never rebases.
  - **Checks.** It runs `check-dupes` and the configured checks, inside the devcontainer when the run used one. The opt-in and checks policy comes from the HEAD before the merge, fixed when the command starts.
  - **Stops.** It stops before the merge when the checks or their context are missing, and stops with an old-to-new ID mapping when it finds duplicates. `renumber` stays a manual command.
  - **Timeouts and retries.** A timeout preserves the interrupted state instead of resetting it, and a retry first checks for a clean state.

  *Rationale:* an ID already used in branch names, commit subjects or dependencies cannot be renumbered unattended.
- **The duplicate check reads the revision it inspects.**
  - It reads the prefix and config from that revision, and includes drafts.
  - A missing `backlog` executable fails the hook, and only warns when run by hand.
  - A ref with no backlog directory passes explicitly.

  *Rationale:* the hook fails closed, so it must not quietly do less.
- **The plugin's pre-push body.**
  - It enforces on the clone switch and buffers stdin.
  - It runs `check-dupes` on every pushed sha, skips deletions, and is tested on them.
  - It is chained through `.git/hooks/pre-push.local`, and fails closed when the plugin cannot be resolved.

  *Rationale:* a duplicate arrives with no git conflict.
- **No task creation inside a run.** A plugin PreToolUse guard refuses `backlog task create` and the shared-backlog `create` when `RALPH_AUTONOMOUS=1` (set by the orchestrator and passed into the container) and the clone switch is on. The template `CLAUDE.md`'s Autonomous Mode text tells the agent to record follow-ups in its notes instead. *Rationale:* the container cannot publish an ID.
- **`/ralph-handoff` in an opted-in destination.** It runs the plugin's `create` with the destination as cwd, and reports the ID as final only after `create` returns 0. Otherwise it keeps today's uncommitted, provisional behaviour. *Rationale:* owner decision.
- **R-INFRA-6 allows only these on master:**
  - the master-branch guard's allowlist paths;
  - `task-N: ` commits that change only task files under `backlog/{tasks,drafts,archive,completed}/`;
  - merges of a reviewed `task-*` branch through the existing lifecycle;
  - `integrate`'s merge of the configured origin base branch.

  For both kinds of merge, equality with `git merge-tree` is an extra check that nothing was resolved by hand. A hand-resolved merge reruns the reviewer before it is pushed. *Rationale:* a clean merge proves no manual resolution, not that the merged-in work was approved.
- **`commit-msg` finds the merge message with `git rev-parse --git-path MERGE_MSG`.** The git hooks are tested in linked worktrees. *Rationale:* worktrees are now on the main path.
- **Network calls are bounded.** Each git network call keeps BatchMode, ConnectTimeout and the HTTPS low-speed limits, and each operation also gets a total deadline. *Rationale:* per-connection limits do not stop a connection that is up but stalled.
- **This repo only: version-tag clashes.** `integrate` stays generic and stops on a manifest version conflict. A re-bump, retest and fresh tag go through the repo's release process, and an existing tag is never moved. Release validation checks that each tag matches its content. *Rationale:* a tag clash can happen even when the merge is clean.

**Scope cuts:**

- No per-host ID ranges or prefixes.
- No `backlog doctor --fix`.
- No automatic renumber inside `integrate`.
- No task creation inside autonomous runs.
- No provisional IDs offline.
- No batch migration across projects.
- No rebase anywhere in the protocol.

**Acceptance criteria (sketch):**

- **`create` in a stale clone.** In each of these clones, `create` publishes a task whose ID is free on origin, and leaves the user's branch, index and working tree unchanged:
  - a clone behind origin;
  - a clone ahead of origin;
  - a dirty clone;
  - a clone with a task branch checked out.
- **Two `create` calls racing** from two clones of one origin end with distinct IDs on origin and no duplicate.
- **A push that succeeded but whose outcome looked unclear** is not repeated: the retry finds the operation trailer on origin and creates no second task.
- **`create` with origin unreachable** exits 2 and leaves no commit and no task file.
- **Two pickers in two clones racing** for the same unassigned task: exactly one claim lands, and the other run moves to the next candidate.
- **`claim`** treats a bare `@claude` as unassigned, and refuses a task held by `@other` without `--force`.
- **A delegated run's claim.** A run launched by holder X claims as X inside the devcontainer.
- **`integrate` on a merged tree with duplicate IDs** stops with an old-to-new mapping and does not push.
- **`integrate` with checks on a changed tree.**
  - It runs the configured checks inside the devcontainer when the run used one.
  - It uses the pre-merge checks policy when the merged-in commits change the `checks` value.
- **`push.py` and rejected pushes.** It retries only a non-fast-forward rejection. An auth failure, a hook refusal and an unreachable origin are each reported and not retried.
- **pre-push with a duplicate.**
  - It refuses a push whose tip has a duplicate ID, including one carried by a draft.
  - It refuses when `backlog` is missing.
  - It passes a branch deletion.
  - It keeps enforcing after a commit that removes the marker, while the clone switch is on.
- **The mid-run guard.** Inside an autonomous run in an opted-in project, `backlog task create` is refused.
- **`/ralph-handoff` into an opted-in destination** reports the ID only after the push lands. Into a destination that hasn't opted in, it leaves the file uncommitted and calls the ID provisional.
- **R-INFRA-6 review fixtures.** The reviewer approves an `integrate` merge of origin that git made cleanly, and flags a hand-edited merge.
- **`commit-msg` in a linked worktree** recognises a merge in progress.
- **The ported test suite passes under bash 3.2,** and the new cases do too.

**Implementation checklist:**

1. **Import the stage-1 files unchanged** from `af5b1f8` into the plugin as a baseline commit: the script, its pre-push body and its tests. This is an interactive step on the host, because the devcontainer sees only this repo.
2. **Harden the script.**
   - The protocol lock and the worktree-based `create`, with an operation trailer, reconcile-before-retry and refusal when offline.
   - The claim rules: bare `@claude`, multiple assignees, rechecking an already-held claim.
   - `integrate` without automatic renumber, with policy fixed at invocation, preserved interrupted state and a total timeout.
   - `check-dupes` reading its settings from the inspected revision, including drafts, and failing closed when `backlog` is missing.
   - The `usage()` fix.
   - Tests for all of the above.
3. **The project shim and clone switch:** the `disable` command, the holder default, and the per-clone migration step. This depends on the base design's resolver and migration tasks.
4. **The plugin pre-push body,** with tests: buffered stdin, several refs, deletions, missing `backlog`, a marker removed while the switch is on.
5. **`push.py`:** publish through `integrate` after each iteration in opted-in projects, classify push failures, run checks in the devcontainer, and enforce the process-tree timeout.
6. **The picker:** the claim lifecycle, `tasks=N` refusing another holder's task, `Assignee` parsing, and the template `CLAUDE.md` Autonomous Mode text.
7. **The mid-run creation guard,** and `RALPH_AUTONOMOUS` passed through to the container.
8. **`/ralph-handoff` through the protocol** in opted-in destinations, with tests for stale destination clones.
9. **The R-INFRA-6 rewrite,** with fixtures for both kinds of merge.
10. **The `commit-msg` `MERGE_MSG` fix,** and git hook tests in linked worktrees.
11. **This repo:** release validation that each tag matches its content, and the manual re-bump procedure documented.

---

## Addendum: decisions from the PRD review (added 2026-11-04)

### Why

A review of the first PRD found that two behaviours were underspecified:

- **When git hooks block.** The base design blocked commits whenever the tracked marker was present. The shared-backlog addendum, by contrast, enforces through a trusted clone-level switch.
- **What `--no-push` means in an opted-in clone.** That clone has to push to claim a task.

### What changed

- **Commit blocking now follows a per-clone switch.** The per-clone migration sets `git config ralph.pluginHooks true`.
  - With the switch on, pre-commit and commit-msg block when the plugin cannot be resolved.
  - pre-push blocks when either `ralph.pluginHooks` or `ralph.sharedBacklog` is on. Its repair message names `git push --no-verify`.
  - The marker still declares the project's intent, and the migration reads it.
  - A commit that removes the marker does not stop enforcement.

  This replaces the "marker present" row in the base design's failure table.
- **In an opted-in clone, `--no-push` is allowed only with `tasks=N` for a single task.** The claim is still pushed, because it is coordination rather than work. The finished work is not published until the operator runs `integrate`.

### Implementation checklist

- The PRD (`design/plugin-delivered-project-files-prd.md`) carries both decisions in its stories and functional requirements.
