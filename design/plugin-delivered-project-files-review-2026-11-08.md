# Feature Review: plugin-delivered-project-files (2026-11-08)

**Verdict: Aligned**

The feature does what the design asked for. All 26 user stories and all 13 functional requirements are delivered, no non-goal ships, and no brainstorm scope cut is broken. Every finding that kept the 2026-11-07 review at Partial has been fixed by TASK-333 to TASK-341. Two things remain, both with a clear path:

- TASK-340 is To Do. It holds the two real-devcontainer host checks.
- PRD US-003 and the brainstorm's shim section were not updated after TASK-341 changed the shim design.

The notes below also list a few minor gaps.

**Passes run:** 1, 2, 3, 4, 5
**Passes skipped:** none. The PRD has Non-Goals and Success Metrics sections, and the brainstorm has Scope Cuts.

**Review range:** `5a50f4e..d91ad07`. It touches 223 files, +18,901/−890 lines; outside `backlog/` and `design/` it is 172 files, +16,790/−670. The judgement covers the 40 Done tasks labelled `feature:plugin-delivered-project-files`: TASK-295 to TASK-323, TASK-328, TASK-329, TASK-332 to TASK-339 and TASK-341. Every one of them has all its ACs checked. TASK-340 carries the label but is To Do, so it is out of scope as a Done task.

**Attribution: unlabelled tasks in the range, left out of the judgement**

| Task | What it changed |
|---|---|
| TASK-324 | Skip list in `loop.py`, `tasks.py`, `prompts.py`, `status.py` and `summary.py`, the status fixtures, and the ralph-status and ralph-status-watch SKILL.md files |
| TASK-325, TASK-326 | The `Bash(git *)` and `Bash(gh *)` `if:` filters in `hooks.json` and `.claude/settings.json`, and the lexers of both commit guards |
| TASK-327 | The `push` parameter in ralph-run SKILL.md |
| TASK-330 | Retired this repo's `.claude/hooks/filename-length-guard.sh` |
| TASK-331 | `.claude/hooks/install-clone-hooks.sh`, and a SessionStart hook that only reports, `clone-hooks-session-check.sh` |

Also in the range: the prior review document, `design/plugin-delivered-project-files-review-2026-11-07.md` (commit 87be6e8), and backlog-only commits that rework or add tasks.

**What the reviewer verified (macOS sandbox, HEAD d91ad07, clean tree):**

- **ruff:** `uv run ruff check .` reports all checks passed.
- **pytest:** 1576 passed, 8 skipped, 3 failed. All three are the known sandbox-only failures:
  - `test_claims.py::test_the_delegated_holder_claims_inside_the_container` (mktemp in `/tmp` is denied);
  - `test_shared_backlog_enable.py::test_enable_asks_once_for_the_holder_on_a_terminal` (needs a pty);
  - `test_shared_backlog_recovery.py` (the sandbox cannot kill the git push client).
- **bats `tests/unit`:** 223/223.
- **bats `tests/integration` and `tests/e2e`:** with network denied they fail because `uv run` cannot reach pypi. With pypi allowed, 52/59 pass. The 7 that still fail come from two files the range does not touch:
  - `tee-buffering.bats` is a pure bash/tee test with no repo code in it;
  - `usage-pause.bats` fails because `uv run` puts `/opt/homebrew/bin` ahead of the test's mocked `backlog`.

  Both are environment problems, not defects of this feature.
- **Shell suites under `/bin/bash` 3.2.57, with nested bash also 3.2:**

  | Suite | Passed | Failed |
  |---|---|---|
  | lock | 65 | 0 |
  | claim | 57 | 0 |
  | retry | 38 | 0 |
  | create | 56 | 0 |
  | integrate | 82 | 0 |
  | prepush | 44 | 0 |
  | recovery | 44 | 8 |

  The recovery failures are the known sandbox limit. TASK-308's notes record 52/0 for it outside the sandbox on 2026-11-08.
- **`bash -n` under 3.2:** clean on `plugins/ralph/git-hooks/run` and `templates/shims/git-hook`.
- **R-INFRA-6 on this repo's own history:** `master-provenance.sh 14486ba..master` with `CLAUDE_PROJECT_DIR` set to the repo. All 47 first-parent commits are `ok`, none flagged, rc=0.
- **This clone's live state:**
  - `pre-commit`, `commit-msg`, `post-commit` and `pre-push` are all shim v2 (sha256 1520d251…, equal to the template).
  - `post-commit.local` and `pre-push.local` are present.
  - git config has `ralph.pluginHooks=true`, `ralph.projectPath` and `ralph.jq`.

## Intent → Implementation Matrix

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| US-001 | Registry resolver | Delivered | `templates/shims/resolve-plugin.sh` takes the first applicable entry in registry order: user scope anywhere, project or local scope only where `projectPath` equals the identity (TASK-321). It rejects a separate git dir, and each failure has its own message. Its copies in ralph.sh, refine.sh, the git-hook shim and the shared-backlog shim are kept byte-identical by `test_resolve_plugin.py`. No `sort -V` over the cache remains. Both registry orders were checked on the host (TASK-295 AC #9, TASK-321 AC #6). |
| US-002 | Guards as plugin hooks behind a marker gate | Delivered | `plugins/ralph/hooks/hooks.json` has the 13 `run.sh` entries plus the ungated autonomous-create-guard. `run.sh` resolves the canonical root, gates on `pluginHooks` and `localGuards`, uses the payload's cwd and exports `RALPH_PROJECT_ROOT`. All 7 guards are present. The template-copy clause was superseded by US-007. The filters were later widened by the unlabelled TASK-325 and TASK-326. |
| US-003 | Git hook bodies and the fixed shim | Delivered | The four bodies are in `plugins/ralph/git-hooks/`. Since TASK-341 the shim execs `git-hooks/run`, which runs `<name>.local` first (pre-push stdin is copied once), stops on its failure, then runs the body. The shim fails closed per switch when the plugin is unresolved. commit-msg uses `--git-path MERGE_MSG`. Covered by `test_git_hook_shim.py`, including core.hooksPath and linked worktrees. PRD line 117 still describes the pre-TASK-341 shim (see the Drift List). |
| US-004 | User-settings fragment | Delivered | Checked with jq: `user-settings.json` has 46 `Bash(...)` rules plus `ScheduleWakeup`, `attribution` with empty commit and PR trailers, `sandbox` with `enabled` and `autoAllowBashIfSandboxed`, and 0 `Skill(...)` rules. The preflight check is report-only, and there is a non-overwriting `merge-user-settings.sh`. The host `/ralph-status` check is recorded (TASK-298 AC #5). |
| US-005 | Tracked migration | Delivered | `migrate-plugin-hooks.sh tracked` writes the marker first, has stop points for each interruption, and a second run changes nothing. `--retire-legacy` was added by TASK-323. |
| US-006 | Clone migration and preflight states | Delivered | `clone` installs shims in `--git-path hooks` and refuses with `DEVCONTAINER=true`. It replaces any shipped body or past shim listed in `shipped-git-hooks.sha256`, never overwrites a `.local`, and warns when an accepted hook is a modified copy of a body (TASK-339). The preflight reports not migrated, partially migrated, shims missing, shims outdated, and that guards are best effort. `managed-file-drift.sh` finds hooks where git does (TASK-336). |
| US-007 | Init and Upgrade use the plugin | Delivered | `templates/claude/hooks/` and `templates/git-hooks/` are gone. Init Step 3.11 and Upgrade U4 run tracked plus clone, and the second host runs clone only (ralph-init SKILL.md lines 458 and 761). The README describes the marker, the switches, the shims and the migration. |
| US-008 | Migrate this repo, with host checks | Delivered | `.claude/ralph.json` lists all six live guards in `localGuards`. Host evidence for AC #2 to #7 is recorded on both hosts (TASK-302). pre-push sits behind the shim after a recorded live bumped push (TASK-328). |
| US-009 | Stage-1 import and baseline | Delivered | The sha256 values are pinned and `tests/shell/stage1/*.orig` exists. The harness ran 75/75 under 3.2 (TASK-303). |
| US-010 | Locks and deadlines | Delivered | Token-owned mkdir locks, reclaim only on the same host, pid namespace and dead pid, and `with_deadline`. The 3.2 run is recorded (TASK-304, 2026-11-08), and the reviewer reran the suite: 65/0. |
| US-011 | Claim rules, check-dupes and help | Delivered | `real_assignees` and `held_by_holder` implement the claim rules. check-dupes reads the REV's config, includes drafts, and fails when backlog is missing. `--help` exits 0. 3.2 run recorded (TASK-305), and the reviewer got 57/0. |
| US-012 | Merge-only retry | Delivered | `land_reapply` handles the retry. The script contains no rebase command; the word appears only in comments and state checks. Retry suite 38/0 under 3.2 (TASK-320 AC #6, and the reviewer's run). |
| US-013 | Create in a temporary worktree | Delivered | `cmd_create` and `create_worktree` carry an op-ID trailer, exit 2 when offline, and refuse while untracked task files exist. 3.2 run recorded (TASK-307), and the reviewer got 56/0. |
| US-014 | Reconciliation and recovery refs | Delivered | `create_reconcile`, plus `refs/ralph/recovery/<op>` written from the EXIT trap. TASK-308 records 52/0 under 3.2 outside the sandbox. |
| US-015 | integrate without renumber | Delivered | It merges with an `Integrated-Origin` trailer, fixes its policy from HEAD before the merge, refuses over a left merge state with `require_settled`, stops with a `renumber_plan` mapping, and retries only a non-fast-forward. 3.2 run recorded (TASK-309), and the reviewer got 82/0. |
| US-016 | Project shim, enable and disable | Delivered | `templates/shims/shared-backlog.sh` exists. `cmd_enable` requires the marker, asks once for the holder on a terminal, keeps an existing pre-push as `.local`, replaces a past shim in place (TASK-335) and sets the switch last. `cmd_disable` exists, and Init Q5 and Upgrade U4 offer the opt-in. |
| US-017 | Plugin pre-push duplicate check | Delivered | `git-hooks/pre-push` acts only on the switch, buffers stdin, skips deletions and takes no lock. Prepush suite 44/0 under 3.2. |
| US-018 | Publishing lifecycle | Delivered | `loop._publish_iteration` also publishes after a timed-out iteration and after an `on-error=continue` failure (TASK-337). `_publish_end_of_run` skips when an earlier publish failed. `no_push_refusal` and `classify_push_failure` cover the other ACs. |
| US-019 | Checks in the devcontainer, with a timeout | Delivered (live check open) | `checks_context.py` tags the process tree and reaps it through `/proc`. `push.integrate` has a total timeout, kills the process tree, and reports the merge state without resetting it. Tested against a fake devcontainer only; the real-container check is TASK-340 AC #1 (To Do). |
| US-020 | Assignee parsing and eligibility | Delivered | `tasks.py` has `_parse_assignees`, `held_by_other` and `resolve_holder`. CLAUDE.md and its template state the rule. |
| US-021 | Claim lifecycle for runs | Delivered | `claims.py` has `RunSession` and `claim_next` (sync, claim, check again, move to the next candidate). `--force-claim` exists, and `devcontainer_prefix` forwards the holder and the token. Covered by the two-clone race test and the host end-to-end check (TASK-320 AC #4). |
| US-022 | No task creation in autonomous runs | Delivered (live check open) | `autonomous-create-guard.sh` is wired outside `run.sh`. It refuses task create, draft create and draft promote (TASK-332), `shared-backlog.sh create`, the handoff skill and a direct `handoff-create.sh create` (TASK-338). `RALPH_AUTONOMOUS` is set on the host and through `--remote-env`. The in-container env check is TASK-340 AC #2. |
| US-023 | /ralph-handoff state table | Delivered | `handoff-create.sh` mode and create cover all four states. Tests cover destinations that are behind, ahead, dirty and on a task branch. |
| US-024 | R-INFRA-6 merge provenance | Delivered | `master-provenance.sh` and the rewritten rule exist, and the Review step records the reviewed SHA. The reviewer's run over this repo's history: 47 ok, 0 flagged. TASK-329 extended it to nested projects. |
| US-025 | Release tag validation | Delivered | `version-bump-guard.sh` has `check_release_tag` and `is_release_of`, runs `ls-remote` under a watchdog, and is covered by bats fixtures. `.claude/RELEASING.md` step 2 is now merge-only (TASK-334). |
| US-026 | Release the protocol | Delivered | The gate and its override are removed; a grep finds only the test that asserts the gate is absent (`test_shared_backlog_enable.py:112`). The README section exists, and the host end-to-end check is recorded (TASK-320). |
| FR-1 | Marker keys | Delivered | `pluginHooks`, `localGuards`, `sharedBacklog` and `checks` are all read. `.gitignore` has `!.claude/ralph.json`. |
| FR-2 | Clone config keys and their writers | Delivered | grep finds only `migrate-plugin-hooks.sh`, `cmd_enable` and `cmd_disable` writing `ralph.*`. |
| FR-3 | Plugin found only by the resolver | Delivered | No cache scan remains. As before, `handoff-create.sh` runs the calling session's plugin copy, which is acceptable. |
| FR-4 | Hook gating, with the guard exception | Delivered | The `run.sh` gate; autonomous-create-guard keys only on `RALPH_AUTONOMOUS` and the switch. |
| FR-5 | Blocking when the plugin is missing | Delivered | The shim's per-switch table. Since TASK-341 the check is whether `git-hooks/run` resolves (see note 4). |
| FR-6 | Holder resolution | Delivered | `--as`, then the env var, then git config; resolved once per run; a bare `@claude` counts as unassigned in both the script and the picker. |
| FR-7 | Locks | Delivered | Token ownership; read-only validation takes no lock. |
| FR-8 | Publishing a task ID | Delivered | `create` refuses offline and reconciles before it retries. |
| FR-9 | No automatic renumber or rebase | Delivered | `renumber` is manual only. |
| FR-10 | Exit codes | Delivered | 0, 1, 2 and 64 in the header and the code (`usage` exits 64). |
| FR-11 | Deadlines | Delivered | `SHARED_BACKLOG_DEADLINE`, default 120 s, preserves state on expiry. |
| FR-12 | Portability | Delivered | The static guard covers the new `git-hooks/run`. 6 of 7 suites pass under real 3.2 in the reviewer's run, and recovery is recorded on the host. |
| FR-13 | Release gate | Delivered | The gate existed from TASK-310 to TASK-320 and was opened by US-026. |

## Non-Goal Violations

None detected.

- `.devcontainer/`, its template and `.claude/brainstorm-rules.md` have no diff in the range.
- `CLAUDE.md` is still a per-project copy; only its text changed, which US-020, US-022 and US-024 required.
- There is no batch migration: the scripts take one project directory.
- The shipped `hooks.json` has no SessionStart entry, and there is no pointer file. The repo-only SessionStart hook (TASK-331) only runs `install-clone-hooks.sh --check` and never writes `.git/hooks`.
- Nothing mentions Codex, and nothing runs `doctor --fix`.
- No automatic path renumbers or rebases, `create` refuses offline, and autonomous creation is guarded (best effort).

## Scope Cut Violations

None detected.

- The cut the prior review flagged, "drops `install-hooks`", now holds. TASK-333 removed it: `grep -rn install-hooks README.md plugins/` is empty, and a claim-suite test asserts it ends in a usage error.
- The base brainstorm said the `.git/MERGE_MSG` fix "gets its own task". Its own addendum (checklist item 10) and PRD US-003 later folded it into the protocol work. That is superseded, not violated.

## Success Metric Assessment

| Metric | Status | Notes |
|--------|--------|-------|
| No per-project runs for guard and git-hook changes | Hypothesis, with mechanism evidence | The shim and `hooks.json` resolve the registered install on every call. Body changes arrive with `/plugin update`: TASK-328 picked up the new pre-push body, and TASK-302 AC #7 showed it on the second host. TASK-341 moved the chaining into the plugin, so only the resolver and the fallback now need a shim refresh. TASK-341 itself still cost one `clone` per clone, plus a manual pre-push replacement on both hosts (note 2). Nothing measures this across projects. |
| No leftovers from migration | Measurable | Tests cover no commits, an idempotent second run, and every interruption point, for both `tracked` and `clone`. |
| No duplicate IDs on origin | Measurable | pre-push runs check-dupes on every pushed SHA, drafts included. Racing creates are tested, and the host end-to-end check confirms it; `check-dupes origin/master` can be rerun at any time. It can be bypassed with `--no-verify`, or by pushing from a clone without the switch. |
| No double work | Partially measurable | Holds for Ralph runs: the two-clone race test and the host end-to-end check with two orchestrator runs. The interactive Task Lifecycle has no claim step, so an interactive session can start a task another host's run has claimed. |

## Drift List

- **`baa1db5` (TASK-315), carried over from the prior review.** This is a mechanical ruff cleanup across about 30 files unrelated to claims, such as `usage_check.py`, `devcontainer.py`, `refine/loop.py` and many test files. It traces only to the "ruff passes" AC. Behaviour is unchanged. It is in history and cannot be undone; it is minor.
- **Design docs describe the old shim (TASK-341).** TASK-341 is labelled and traces to its own ACs, so this is not creep. But it changed a locked design point, and neither design document was updated:
  - `design/plugin-delivered-project-files-prd.md:117` (US-003) still says the shim "execs `<installPath>/git-hooks/<name>`".
  - `design/plugin-delivered-project-files-brainstorm.md:71` says the shim is "never changed after install".
  - Brainstorm lines 77–78 put the `.local` chaining in the shim.

  The README and SKILL.md do describe the new design. A one-line superseded note, like the TASK-321 one at brainstorm line 76, would close this.
- **TASK-329, nested-project support in `master-provenance.sh`.** It goes beyond PRD US-024 but traces to TASK-329's own ACs. Noted, but not counted as creep.

## Reviewer Notes

1. **The 2026-11-07 review's findings and what fixed them:**

   | Finding | Fixed by |
   |---|---|
   | `install-hooks` still shipped; sibling-project text and the owner's name in messages | TASK-333 |
   | Unrecorded host 3.2 runs | 3.2 notes dated 2026-11-08 in TASK-304, 305, 307, 308 and 309 |
   | R11 table and RELEASING.md rebase advice | TASK-334 |
   | Spaces in project paths not documented | TASK-334 (README) |
   | No past-shim hashes in `shipped-git-hooks.sha256` | TASK-335 and TASK-341 |
   | Drift script ignored core.hooksPath and worktrees | TASK-336 |
   | Failed iterations that moved master went unpublished | TASK-337 |
   | Direct `handoff-create.sh create` not guarded | TASK-338 |
   | A modified body copy kept as `.local` runs twice | TASK-339 |
   | No real-devcontainer checks | Filed as TASK-340, still To Do |

   One bookkeeping leftover: TASK-306 AC #5 is checked, but its notes carry only the host deferral. The 3.2 retry evidence is recorded in TASK-320 AC #6 instead.

2. **Refreshing the pre-push shim is not covered by the documented path.**
   - `migrate-plugin-hooks.sh clone` manages only pre-commit, commit-msg and post-commit.
   - The preflight's `_SHIMMED_HOOKS` (`preflight.py:81`) leaves out pre-push, so it never reports an outdated pre-push shim.
   - `.claude/RELEASING.md:15` and the README say to refresh with "`/plugin update`, then `clone`".
   - In a shared-backlog clone, rerunning `shared-backlog.sh enable` does replace a past pre-push shim (TASK-335), but no document says so. Both hosts replaced pre-push by hand (TASK-341 host notes).

   The impact is low: the v1 shim still works with 0.25.11, because it execs `git-hooks/pre-push` with its own chaining. But future changes to the dispatcher will not reach that hook. A fix would be to include pre-push in the preflight check, and either have `clone` replace a pre-push that is a recorded shim or document "rerun `enable`".

3. **The preflight judges shim versions against the plugin copy it runs from.** It compares against the shim under its own plugin root (`_PLUGIN_ROOT` from `__file__`, `preflight.py:66`), not against the registered `installPath`. The second host's note says the preflight reported no drift while the hooks were still v1. The likely cause is that the session's ralph-run copy predated the `/plugin update`; this is inferred, not reproduced. Either document "restart the session after `/plugin update`", or compare against the resolved install.

4. **A small change to FR-5 behaviour with TASK-341.** The shim now fails closed only when `git-hooks/run` cannot be resolved. If an install ships `run` but lacks the body for a hook name, the dispatcher warns and exits 0, even with `ralph.pluginHooks` true; this is pinned by `test_dispatcher_warns_and_exits_0_after_local_for_a_name_without_body`. Before TASK-341 the shim resolved `git-hooks/<name>` itself, so a missing body blocked. All four bodies ship today, so nothing is exposed now, but a partial install would get through with only a warning instead of being blocked.

5. **Open live checks.** TASK-340 covers the reaper and `RALPH_AUTONOMOUS` in a real container. The forwarding of `SHARED_BACKLOG_HOLDER` and `RALPH_RUN_LOCK_TOKEN` into a real container is also only fake-tested. It uses the same `--remote-env` path, so it could be added as one line to TASK-340 AC #2.

6. **The "interactive sessions" host check used `claude -p`.** TASK-302 AC #2 was run with `claude -p` sessions, not an interactive TUI. The hook path is the same, so the risk is low. This repo lists all six guards in `localGuards`, so the plugin guard path runs only in test projects, never in this repo's own sessions.

7. **Leftover Skill rules.** The template `settings.local.json` still ships 7 short-name `Skill(...)` rules. The README says plugin skills need none, and TASK-298's host check confirmed it. This is harmless, and it is consistent with US-004, which covers only the fragment.

8. **Suggested follow-ups (none blocks Aligned):**
   - Add superseded notes for TASK-341 to the PRD and brainstorm.
   - Close the pre-push refresh gap from note 2.
   - Run TASK-340 on the host.
   - Optionally record the TASK-306 3.2 cross-reference.

Key files:
- `plugins/ralph/skills/ralph-init/templates/shims/git-hook`
- `plugins/ralph/git-hooks/run`
- `plugins/ralph/skills/ralph-run/scripts/ralph/preflight.py`
- `plugins/ralph/skills/ralph-init/scripts/migrate-plugin-hooks.sh`
- `plugins/ralph/scripts/shared-backlog.sh`
- `design/plugin-delivered-project-files-prd.md`
- `design/plugin-delivered-project-files-brainstorm.md`
- `.claude/RELEASING.md`
- `backlog/tasks/task-340 - Check-the-integrate-reaper-and-RALPH_AUTONOMOUS-in-a-real-devcontainer.md`
