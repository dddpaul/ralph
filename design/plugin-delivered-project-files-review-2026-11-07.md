# Feature Review: plugin-delivered-project-files (2026-11-07)

**Verdict: Partial**

The feature is close to Aligned. All 26 user stories and 13 functional requirements are implemented, and no non-goal is shipped. Three things keep it at Partial, and each is cheap to fix:

1. A locked brainstorm cut was not kept: `install-hooks` is still in the script.
2. Three Done tasks have their (host) bash 3.2 criterion unchecked, and a fourth has it checked with no recorded run.
3. The shipped script still carries leftover text from the sibling project.

**Passes run:** 1, 2, 3, 4, 5. **Passes skipped:** none. The PRD has Non-Goals and Success Metrics, and the brainstorm has Scope Cuts.

No `.claude/ralph-review-rules.md` exists, so only the standard rubric applied.

**Review range:** `5a50f4e..18591c8`, from the parent of TASK-295's first commit, `4841bdd`, to master at review time. It covers 211 files, +17,395/−849 lines. The 32 Done tasks labelled `feature:plugin-delivered-project-files` are 295–323, 328, 329 and 332.

**Attribution.** The range also holds unlabelled tasks. They were attributed and left out of the judgement:

| Task | Change |
|------|--------|
| TASK-324 | Skip list in loop, tasks, prompts and status |
| TASK-325, TASK-326 | `Bash(git *)` and `Bash(gh *)` filters in hooks.json, and the guard lexers |
| TASK-327 | `push` parameter |
| TASK-330 | Retiring this repo's `.claude/hooks/filename-length-guard.sh` |
| TASK-331 | `install-clone-hooks.sh` and a report-only SessionStart check |

**Verified by the reviewer:**

- ruff is clean, and bats `tests/unit` passes 224/224.
- pytest: 1508 passed, 8 skipped, 1 failed. The failure, `test_claims.py::test_the_delegated_holder_claims_inside_the_container`, is the sandbox's: `mktemp` in `/tmp` is denied because the fake container env has no TMPDIR. The recovery and enable tests were deselected because of the known sandbox limits.
- The shell suites ran under `/bin/bash` 3.2.57, with a PATH wrapper so that nested `bash` was also 3.2. Six suites pass with 0 failures: lock (65), claim (55), retry (38), create (56), integrate (82) and prepush (44). Recovery gives 44 passed and 8 failed, because the sandbox can't kill the `git push` client, so that suite is still unverified under 3.2.

## Intent → Implementation Matrix

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| US-001 | Registry resolver | Delivered | `templates/shims/resolve-plugin.sh`, embedded byte-identically in ralph.sh, refine.sh, git-hook and the shared-backlog shim (parity checked in `test_resolve_plugin.py`). It takes the first applicable entry in registry order (TASK-321) and rejects a separate git dir. No `sort -V` over the cache remains. The host check of both registry orders is recorded (TASK-295, TASK-321). |
| US-002 | Guards as plugin hooks behind a marker gate | Delivered | `plugins/ralph/hooks/{run.sh,hooks.json}` and 7 guards. hooks.json has 13 entries plus autonomous-create-guard. run.sh checks the marker and `localGuards`, exports `RALPH_PROJECT_ROOT`, and uses the cwd from the payload. The template-copy clause was superseded by US-007. |
| US-003 | Git hook bodies and the fixed shim | Delivered | `plugins/ralph/git-hooks/*` and `templates/shims/git-hook`. It chains `.local` with buffered stdin, fails closed per switch, and uses `--git-path MERGE_MSG`. `test_git_hook_shim.py` covers core.hooksPath and linked worktrees. |
| US-004 | User-settings fragment | Delivered | `plugins/ralph/user-settings.json`: 46 Bash rules, ScheduleWakeup, attribution and sandbox, with no Skill rules. Also a preflight check and `merge-user-settings.sh`. The host `/ralph-status` check is recorded. |
| US-005 | Tracked migration | Delivered | `migrate-plugin-hooks.sh tracked` writes the marker first, merges, adds the `.gitignore` exception, and has stop points. Covered by `test_every_interruption_point_still_enforces`. TASK-323 added `--retire-legacy`. |
| US-006 | Clone migration and preflight states | Delivered | The `clone` subcommand puts shims in `--git-path hooks` and never overwrites a `.local`. It sets the switches but never sharedBacklog, and refuses inside the devcontainer. `preflight.py` has `migration_state`. The drift-script gap is in note 2c. |
| US-007 | Init and Upgrade use the plugin | Delivered | The template guards, git-hook bodies and settings.json are deleted. SKILL.md Step 3.11 and U4 run tracked plus clone, and the second host runs clone only. The README covers the marker, the switches and the shims. |
| US-008 | Migrate this repo, with host checks | Delivered | `.claude/ralph.json` lists all six live guards in `localGuards`. `.git/hooks/*` equal the shim (`cmp`). Host evidence for AC #2–#7 is recorded on both hosts. TASK-328 later moved pre-push. |
| US-009 | Stage-1 import and baseline | Delivered | The sha256 values are pinned, with `tests/shell/stage1/*.orig` and a harness. A 75/75 run under `/bin/bash` 3.2 is recorded. |
| US-010 | Lock primitives and deadlines | Partial | Implemented and tested. The (host) bash 3.2 criterion, TASK-304 AC #8, is unchecked on a Done task. This review ran the lock suite under 3.2.57: 65 passed, 0 failed. |
| US-011 | Claim rules, check-dupes and help | Partial | Implemented: `real_assignees`, check-dupes reads the REV's config and drafts, and `--help` exits 0. TASK-305 AC #8 is unchecked. This review ran the claim suite under 3.2: 55 passed, 0 failed. |
| US-012 | Merge-only claim and release retry | Delivered | `land_reapply`, and no `git rebase` in the script. The retry suite passes 38/0 under 3.2 (TASK-320 AC #6 and this review). |
| US-013 | Create in a temporary worktree | Delivered | `cmd_create` and `create_worktree`, an op-ID trailer, exit 2 offline, and a refusal for untracked task files. AC #7 is checked with its host part deferred in the notes. This review ran the create suite under 3.2: 56 passed, 0 failed. |
| US-014 | Reconciliation and recovery refs | Partial | `create_reconcile`, and `refs/ralph/recovery/<op>` written from the main shell's EXIT trap. TASK-308 AC #7 is checked, but no `/bin/bash` 3.2 run is recorded anywhere, and the sandbox kept this review from running one. |
| US-015 | integrate without renumber | Partial | A merge with an `Integrated-Origin` trailer. The policy is read from HEAD before the merge, and `require_settled` applies. It stops with a `renumber_plan` mapping and retries only a non-fast-forward. TASK-309 AC #7 is unchecked. This review ran the integrate suite under 3.2: 82 passed, 0 failed. |
| US-016 | Project shim, enable and disable | Delivered | `templates/shims/shared-backlog.sh`. `cmd_enable` requires the marker, asks for the holder once, installs the pre-push shim and sets the switch last. There is also `cmd_disable`, and the opt-in through Init Q5 and U4. |
| US-017 | Plugin pre-push duplicate check | Delivered | `plugins/ralph/git-hooks/pre-push` acts only on the switch, buffers stdin, skips deletions and takes no lock. The prepush suite passes 44/0 under 3.2. This repo's pre-push sits behind the shim (TASK-328, with a live push recorded). |
| US-018 | Publishing lifecycle in push.py | Delivered | `loop._publish_iteration` and `_publish_end_of_run`, `push.no_push_refusal` and `classify_push_failure`. One edge case is in note 4. |
| US-019 | Checks in the devcontainer, with a timeout | Delivered | `checks_context.py` (tagged exec and a `/proc` reaper), and `push.integrate` with a timeout and a tree kill. It is tested against a fake devcontainer only. The real-container follow-up in TASK-313's notes is not recorded. |
| US-020 | Assignee parsing and eligibility | Delivered | `tasks._parse_assignees`, `held_by_other` and `resolve_holder`. CLAUDE.md and its template state the rule. |
| US-021 | Claim lifecycle for runs | Delivered | `claims.py`: RunSession holds the run lock and the delegated env, and `claim_next` claims. Also `--force-claim`, and `devcontainer_prefix` forwards the holder and the token. Covered by the two-clone race test and by the host end-to-end check in TASK-320. |
| US-022 | No task creation in autonomous runs | Delivered | `autonomous-create-guard.sh`, wired outside run.sh. `RALPH_AUTONOMOUS=1` is set on the host and through `--remote-env`. TASK-332 added draft create and promote. Gaps: a direct `handoff-create.sh create` call is not matched, and no in-container env check is recorded. |
| US-023 | /ralph-handoff state table | Delivered | `handoff-create.sh` mode and create cover the four states. The tests use destinations that are behind, ahead, dirty and on a task branch. |
| US-024 | R-INFRA-6 merge provenance | Delivered | `plugins/ralph/scripts/master-provenance.sh` and the rewritten rule. CLAUDE.md and its template record `Review: APPROVED <sha>`, and fixtures exist. Two deviations are documented: bookkeeping commits may follow the reviewed SHA, and a pure fast-forward of a pre-fork commit cannot be detected. |
| US-025 | Release tag validation | Delivered | `version-bump-guard.sh` has `check_release_tag` and `is_release_of`, with `ls-remote` under a watchdog. Documented in `.claude/RELEASING.md` and covered by bats fixtures. |
| US-026 | Release the protocol | Delivered | The gate and its override are removed; grep finds them only in design and backlog files. README has a "Shared backlog across hosts" section. The host end-to-end check is recorded: two creates, two orchestrator claims and an integrate. |
| FR-1 | Marker keys | Delivered | `pluginHooks`, `localGuards`, `sharedBacklog` and `checks` are all read. `.gitignore` has `!.claude/ralph.json`. |
| FR-2 | Clone config keys and their writers | Delivered | Only the migration, enable and disable write `ralph.*` (grep). |
| FR-3 | Plugin found only by the resolver | Delivered | No cache scan remains. Minor: `handoff-create.sh` runs the calling session's plugin copy, not the destination's resolved install. |
| FR-4 | Hook gating, with the guard exception | Delivered | The run.sh gate. autonomous-create-guard keys only on `RALPH_AUTONOMOUS` and the switch. |
| FR-5 | Blocking when the plugin is missing | Delivered | The switch loop in the shim, with the host check in TASK-302 AC #6. |
| FR-6 | Holder resolution | Delivered | `holder_from_args` and `resolve_holder`. A bare `@claude` counts as unassigned in both the script and the picker. |
| FR-7 | Locks | Delivered | Token-owned mkdir locks. check-dupes takes no lock. |
| FR-8 | Publishing a task ID | Delivered | `create` refuses offline and reconciles before it retries. |
| FR-9 | No automatic renumber or rebase | Delivered | `renumber` is manual, and integrate only prints the plan. |
| FR-10 | Exit codes | Delivered | 0, 1, 2 and 64, in the script header and the code. |
| FR-11 | Deadlines | Delivered | `with_deadline` and `protocol_cmd`, with a 120 s default. integrate uses the orchestrator's timeout. |
| FR-12 | Portability | Delivered | The static guard passes, and 6 of the 7 suites pass under real 3.2 in this review. Recovery is unverified. |
| FR-13 | Release gate | Delivered | The gate existed from TASK-310 to TASK-320 and was opened by US-026. |

## Non-Goal Violations

None detected:

- `.devcontainer/`, `.claude/brainstorm-rules.md` and their templates have no diff.
- CLAUDE.md is still a per-project copy; only the template text changed.
- There is no batch migration: the scripts take one project directory.
- hooks.json has no SessionStart entry, and there is no pointer file.
- Nothing mentions Codex.
- There are no per-host ID ranges, and `backlog doctor` runs without `--fix`.
- No automated path renumbers or rebases, and `create` refuses offline.
- The guard covers autonomous creation, as best effort.
- The repo-only SessionStart hook from TASK-331 only reports and never writes `.git/hooks`.

## Scope Cut Violations

**"drops `install-hooks`"** is a locked decision in the brainstorm's shared-backlog addendum (brainstorm line 307), and it was not kept:

- `plugins/ralph/scripts/shared-backlog.sh` still ships `install-hooks [--force]`: header line 33, `cmd_install_hooks` at lines 1059–1074, dispatch at line 1184.
- TASK-320 (dd3aa28) added it to the README command table.
- It installs `scripts/hooks/pre-push`, a stage-1 file that no Ralph project has, so it fails in practice. With `--force` it can replace the plugin pre-push shim with a hook that is not the shim. That is the "second mechanism" the brainstorm's open question warned against.
- The cut was lost between the brainstorm and the PRD: no PRD story and no task AC mentions it.

## Success Metric Assessment

| Metric | Status | Notes |
|--------|--------|-------|
| No per-project runs for guard and hook changes | Hypothesis, with mechanism evidence | The shim resolves the registered installPath on every call (fake-registry tests). After the plugin update, a commit on the second host runs the plugin hooks (TASK-302 AC #7). This clone picked up the newly shipped pre-push body through the plugin update (TASK-328). Nothing measures this across projects. A change to the shim or the resolver still needs a per-clone refresh, and a new hook name needs a per-clone install (see note 3). |
| No leftovers from migration | Measurable | Tests cover no commits, an idempotent second run, and every interruption point for both tracked and clone (`test_migrate_plugin_hooks*.py`). |
| No duplicate IDs on origin | Measurable | pre-push runs check-dupes on every pushed SHA, drafts included. The racing-create tests and the host end-to-end check support it, and `check-dupes origin/master` can be run afterwards. It can still be bypassed with `--no-verify`, or by pushing from a clone without the switch. |
| No double work | Partially measurable | Covered for Ralph runs by the two-clone race test and the host end-to-end check with two orchestrator runs. Interactive sessions are not covered: the interactive Task Lifecycle has no claim step, so the metric holds only for Ralph runs. |

## Drift List

- **`baa1db5` (TASK-315).** This commit is a repo-wide mechanical ruff cleanup across about 30 files unrelated to claims: `usage_check.py`, `devcontainer.py`, `refine/loop.py`, `refine_orchestrator.py`, `tools/__init__.py` and many test files. It traces only to the "ruff passes" AC. Behaviour is unchanged, but it should have been its own chore task.
- **Sibling-project text in shipped code.** `shared-backlog.sh` lines 6–7 point to a "Shared repo protocol" CLAUDE.md section and to `design/multi-host-parallel-work-brainstorm.md`; neither exists in this repo or in Ralph projects. Its refusal messages also name the owner ("on <owner>'s say-so" at lines 747 and 788; "stop and tell <owner>" at lines 1041, 1046, 1052 and 1054). These were kept byte-identical at import and never cleaned up during hardening. TASK-315 logged a follow-up, but no task was filed.
- **The `install-hooks` README row (TASK-320).** Counted under Scope Cut Violations above.
- **TASK-329, nested-project support in `master-provenance.sh`.** This goes beyond PRD US-024. It is a handoff from another Ralph project and traces to TASK-329's own ACs, so it is not creep under the rubric, but it widens the feature past its design documents.

## Reviewer Notes

1. **Done tasks with open host criteria.** TASK-304 AC #8, TASK-305 AC #8 and TASK-309 AC #7 are unchecked. TASK-307 AC #7 and TASK-308 AC #7 are checked, but their notes defer the host part and no run is recorded. The PRD convention says such a task "does not count as complete until the host check is recorded". This review's 3.2.57 runs cover lock, claim, create and integrate. The recovery suite (TASK-308) still needs a real `/bin/bash` 3.2 run outside the sandbox:

   ```
   PATH=<dir with bash -> /bin/bash>:$PATH /bin/bash tests/shell/shared-backlog-recovery-test.sh
   ```

2. **Follow-ups that live only in task notes.** `backlog task list -s "To Do"` is empty, so none of these is tracked:
   - (a) The autonomous guard does not match a direct `handoff-create.sh create` call (TASK-317).
   - (b) Shipped messages contain the owner's name (TASK-315).
   - (c) `managed-file-drift.sh` compares fixed `.git/hooks/<name>` paths (lines 81–83). It skips git hooks unless `$project/.git` is a directory, so it disagrees with clone and preflight under `core.hooksPath`, and it skips linked worktrees (TASK-300, follow-up 1).
   - (d) The R11 table in `.claude/task-reviewer-rules.md` still pairs `.git/hooks/*` with the plugin bodies, and still says settings.json is kept "until the repo migrates (TASK-302)" (TASK-302 F3).
   - (e) An accepted hook that is a modified copy of a plugin body becomes a `.local` that runs the body's work twice (TASK-302 F2; assigned to TASK-323 but not in its ACs).
   - (f) There are no real-devcontainer checks for the US-019 reaper or the US-022 `RALPH_AUTONOMOUS` env.
3. **Shim upgrade path.** `shipped-git-hooks.sha256` lists past hook bodies but no past shim versions. The shim has not changed since 777119a. The first time it does:
   - `clone` will refuse every installed shim unless it is accepted;
   - preflight will report "shims missing in this clone" in every clone;
   - `enable` will move an old pre-push shim to `pre-push.local`, so the plugin body runs twice.

   Adding old shim hashes would make the brainstorm's accepted "shim refresh per clone" work.
4. **Failed iterations that moved master.** In an enforcing clone, an iteration that timed out, or failed under `on-error=continue`, is not published even if it merged to master (the `continue` paths in loop.py). The next claim then dies in `require_level` ("local master is ahead"), the run stops, and only the end-of-run integrate publishes. In practice, `on-error=continue` behaves like stop. TASK-312 flagged this, and TASK-315 did not resolve it.
5. **Rebase advice in RELEASING.md.** `.claude/RELEASING.md:41` says "rebase your unpushed work onto it" after a version conflict. That contradicts the feature's no-rebase stance and breaks R-INFRA-6 provenance, because rebased commits no longer match their `Review: APPROVED <sha>`. Merge only would be consistent.
6. **Spaces in project paths.** `checks_context.devcontainer_env` refuses a project path that contains whitespace, so integrate cannot run checks in the devcontainer for such clones, though the resolver supports spaces. This is documented in the code, but not in the README or the skill.
7. **Leftover Skill rules.** The template `settings.local.json` still ships the 7 `Skill(...)` rules, although TASK-298's host check showed they are not needed. This is harmless and consistent with US-004, which covers only the fragment.
8. **What would make it Aligned:**
   - Remove `install-hooks` and its README row, or record an owner decision to keep it.
   - Record the 3.2 results and check TASK-304 #8, TASK-305 #8 and TASK-309 #7.
   - Run the recovery suite under 3.2 on the host.
   - Remove the sibling-project references and the owner's name from `shared-backlog.sh`.
   - File the follow-ups in note 2 as tasks.

Key files:

- `plugins/ralph/scripts/shared-backlog.sh`
- `README.md`
- `plugins/ralph/skills/ralph-run/scripts/ralph/loop.py`
- `plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh`
- `plugins/ralph/skills/ralph-init/scripts/shipped-git-hooks.sha256`
- `.claude/RELEASING.md`
- `plugins/ralph/skills/ralph-handoff/scripts/handoff-create.sh`
