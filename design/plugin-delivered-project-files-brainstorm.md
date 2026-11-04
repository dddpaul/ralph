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

- **Scope precedence in the real registry:** whether a project-scope install wins over the user-scope one. Verify against Claude Code with a project-scope install.
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
