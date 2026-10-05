---
id: TASK-264
title: >-
  Detect and report ralph-init managed files that are behind the installed
  plugin
status: Done
assignee: []
created_date: '2026-10-04 19:04'
updated_date: '2026-10-05 06:21'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Nothing detects a project whose ralph-init-managed files are behind the installed plugin. The only shipped file that so much as mentions the upgrade command is the docs reviewer-rules template's own header; no hook, no orchestrator step and no status command checks. A project that is never upgraded keeps whatever it received at bootstrap, possibly nothing, and no one finds out. Sweeping the fleet by hand is the workaround for this missing detector, not a process worth keeping.

Put the check where projects actually execute. The established detector contract in this plugin is `plugins/ralph/skills/ralph-init/scripts/stale-runtime-copy.sh`: a `check <target>` mode printing one line per offending item, exit 0 clean, 1 found, 2 usage error, with a `patch` mode that only prints and never writes. Follow it. But note why placement matters: that script is invoked from Init and from Upgrade, and an unrun upgrade is precisely the failure being detected here, so wiring the new check only into Upgrade would make it unreachable in the projects that need it most. The ralph-run preflight runs before every autonomous loop in every project, which makes it the one place a stale project reliably passes through.

Report, do not block. A project behind on managed files must still be able to run — the warning tells the operator to upgrade; it does not abort the loop. An aborting check would turn a cosmetic lag into an outage, and the preflight abort path has caused that here before.

Compare by content, not by a version stamp. Projects carry no record of which ralph-init version scaffolded them, and a content comparison against the shipped template is both available today and more honest: it reports what actually differs rather than what a stamp claims. Resolve the template location through CLAUDE_PLUGIN_ROOT, the same way the existing scripts are invoked.

Do not flag project-owned files. `.claude/task-reviewer-rules.md` is never managed: ralph-init's entire involvement with it is one `!.claude/task-reviewer-rules.md` line in the .gitignore block so that it is tracked, plus a read-only duplicate-heading hint on upgrade. It is deliberately never created, written or overwritten, so that an upgrade can never clobber a project's own rules. A drift report that named it would be wrong and would teach operators to ignore the report.

Guard the file list against drift. The set of managed files already exists in two places — the Upgrade status-table list in ralph-init SKILL.md, and the mirror registry in `tests/unit/template-parity.bats`. A third copy inside the script is a drift risk, so pin it with a test: a managed file added to the status table but not to the script, or vice versa, must fail. If TASK-263 lands after this task and adds another managed file, that test failing is the intended behaviour, not a regression.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A check script under plugins/ralph/skills/ralph-init/scripts/ reports one line per managed project file whose content differs from the shipped template, exiting 0 when clean, 1 when drift is found and 2 on usage error — the same contract as stale-runtime-copy.sh
- [x] #2 The script resolves the template location through CLAUDE_PLUGIN_ROOT and compares file content, with no dependence on a recorded version stamp in the project
- [x] #3 The script never reports .claude/task-reviewer-rules.md or any other project-owned file as drifted — verified by a fixture where that file differs arbitrarily from anything and the script still exits 0
- [x] #4 The ralph-run preflight runs the check and surfaces drift as a warning that does not abort: a fixture project with a drifted managed file completes preflight successfully and the warning names the drifted file
- [x] #5 A test proves detection both ways: a fixture with a modified managed file exits 1 and names that file, and an identical fixture exits 0 with no output
- [x] #6 A test pins the script's managed-file list against the Upgrade status-table list in ralph-init SKILL.md, so a managed file present in one and absent from the other fails
- [x] #7 ralph-init SKILL.md Upgrade references the same script, so the upgrade path and the preflight path report drift from one implementation rather than two
- [x] #8 The script passes shellcheck and works under both GNU and BSD tools per the shell-portability rule — verified by running it on this host
- [x] #9 Gates: uv run ruff check . is clean, uv run pytest passes, and LC_ALL=C node_modules/.bin/bats tests/unit passes with no new failures relative to master
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: add plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh (check <project-dir> → '<path>: outdated|missing' lines, exit 0/1/2; list mode prints the managed-path table) resolving templates via CLAUDE_PLUGIN_ROOT (fallback: the script's own plugin) and comparing content exactly as U2 defines (exact / region above a heading / per-hook / .devcontainer, .obsidian and .git gates). ralph.preflight runs it after the fail-fast checks and prints WARNING lines to stderr, never changing the exit code. U2 points at the script; ralph-run Step 3 tells the agent to relay the warnings. pytest suite tests/python/test_managed_file_drift.py covers both-way detection, project-owned files, preflight non-abort, and pins the list against U2.

Commit: `dd6f3d9` - task-264: report ralph-init managed files behind the installed plugin from preflight and upgrade

Commit: `ad59f1f` - task-264: let ralph-run Step 3 read OK past preflight warnings and name the check-failed warning

Commit: `7574d17` - task-264: bump plugin version to 0.10.0 (minor)

Implemented managed-file-drift.sh (check/list; exit 0/1/2), templates via CLAUDE_PLUGIN_ROOT with the script's own plugin as fallback. Rules mirror U2 exactly (exact; region above '## Project-Specific' / '## Project additions'; per-hook; gates .git/, .devcontainer/, .obsidian/); missing files are reported as 'missing'. Dockerfile/.gitignore stay out (U2 'always skipped'); project-owned files are never read. No patch mode: Upgrade U4 owns the writes. ralph.preflight check 7 runs it with CLAUDE_PLUGIN_ROOT set to its own plugin, prints stderr WARNING lines, never changes the exit code (a script failure becomes a 'could not check' warning). U2 now builds its statuses from the script; ralph-run Step 3 relays the warnings. Tests: tests/python/test_managed_file_drift.py (26, incl. the U2 list pin, mutation-checked both ways) + 3 preflight tests. Gates: ruff clean, pytest 748 passed, bats unit 138 ok with the single pre-existing master failure (R11 settings.local.json shape), shellcheck 0.11.0 clean (via uv tool run --from shellcheck-py), run on host with mawk. Caveat: U2's exact match on .claude/settings.local.json means Docs/Mixed projects (pptx merge) and projects with custom permissions always show it outdated, in upgrade and now in preflight. On this repo the check reports the R11 carve-outs (CLAUDE.md, post-commit, settings.local.json). task-reviewer APPROVED (score 8); both minor doc findings fixed. Plugin bumped to 0.10.0.
<!-- SECTION:NOTES:END -->
