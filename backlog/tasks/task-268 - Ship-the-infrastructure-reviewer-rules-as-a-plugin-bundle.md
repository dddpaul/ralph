---
id: TASK-268
title: Ship the infrastructure reviewer rules as a plugin bundle
status: Done
assignee: []
created_date: '2026-10-05 08:20'
updated_date: '2026-10-05 16:58'
labels: []
dependencies:
  - TASK-267
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Seven of this repository's reviewer rules describe files that ralph-init installs in every project it scaffolds, yet they ship to no project. TASK-262 put the portable review-conduct rules into the agent, and TASK-263 built the mechanism for serving shared rules from the plugin, but the rewrite of TASK-263 that adopted that mechanism named only the docs bundle, so these seven were never carried over. Verified after the merge: `plugins/ralph/skills/ralph-init/rules/` holds only the docs bundle, and none of the seven rules' signature phrases appears anywhere under the shipped agent or rules directory.

- R3 — agent files require valid YAML frontmatter
- R4 — frontmatter changes do not take effect mid-session
- R5 — shell scripts must work on both GNU and BSD tools (as amended by TASK-267 to name macOS bash 3.2)
- R6 — no over-broad shell permission rules
- R8 — hook commands reference scripts, not inline bash
- R10 — do not bypass the master-branch guard
- R15 — PostToolUse hooks must emit JSON via hookSpecificOutput

Ship them as a second plugin-resident bundle beside the docs bundle, through the mechanism TASK-263 already built in `plugins/ralph/agents/task-reviewer.md`, and copy its semantics exactly rather than inventing a parallel scheme:

- The bundle is read through the literal braced plugin-root reference in the agent Markdown, never a shell environment lookup, so the agent and the rules come from the same plugin version.
- Applicability is an explicit setting in `.claude/task-reviewer.conf`, a line such as infra_rules=on or infra_rules=off, last line wins, and any other value is a load error rather than a silent fallback. When the setting is unset, apply the bundle if and only if the project root shows ralph-init's footprint; recommended marker: the project shim at ralph.sh or scripts/ralph/ralph.sh, the two places ralph-run itself looks for it. Document the unset default in the agent file the way the docs default is documented.
- Outcomes stay distinct: loaded, absent or not applied, and ERROR. A bundle that applies but is missing or empty is a load error and a blocking finding.

Rule IDs. Give the bundle its own prefix, as the docs bundle uses R-DOCS-N; R-INFRA-N is recommended. The loader's override detection matches the pattern "replaces R(-[A-Z]+-)?[0-9]+", which already accepts that form, so a project can override one by naming it.

Remove the seven rules from `.claude/task-reviewer-rules.md` once the bundle carries them, and do NOT renumber the rules that remain. TASK-262 set that precedent: the project file kept stable IDs with gaps, so historical task notes that cite them stay valid. This repository has ralph.sh at its root, so under the recommended default it loads the new bundle itself, and removing the rules from the project file leaves no gap in this repository's own reviews. R7 (AI-attribution policy), R11 (template parity) and R12 (markdown consistency, which overlaps R-DOCS-4 for documentation projects) stay project-only and are out of scope here.

This depends on TASK-267 because both change R5: TASK-267 amends its text where it lives today, and this task moves the amended rule. Running them in that order means the bundle ships the corrected rule.

R4 limit, as with TASK-262 and TASK-263: the agent runs from the installed plugin cache, so a live check that the real agent loads the new bundle is only possible after the merge, a plugin update and a reload. Verify statically and through the extracted-loader tests in the run, and record the live check as deferred to post-merge host verification rather than claiming it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A second bundle under plugins/ralph/skills/ralph-init/rules/ states all seven infrastructure rules — agent YAML frontmatter, frontmatter not taking effect mid-session, shell portability including macOS bash 3.2, no over-broad shell permission rules, hooks calling scripts rather than inline bash, not bypassing the master-branch guard, and PostToolUse JSON via hookSpecificOutput — verified by grep for each
- [x] #2 The bundle names no downstream project and no task ID and carries no template-parity rule: grep for parity, stacks, services, channels, core and TASK-[0-9] over it returns nothing
- [x] #3 The agent's loader reads the bundle through the literal braced plugin-root reference, gated by an infra_rules setting in .claude/task-reviewer.conf with the same last-line-wins and invalid-value-is-a-load-error semantics as docs_rules, and the unset default is documented in plugins/ralph/agents/task-reviewer.md
- [x] #4 tests/unit/task-reviewer-rules-loading.bats covers the new bundle through the extracted loader: loaded when on, not applied when off, the unset default both ways, an invalid value as a load error, and a missing bundle that applies as a load error
- [x] #5 The rule IDs use a bundle prefix that the loader's override detection matches, verified by a test in which a project rule naming one of them is reported under override references
- [x] #6 The seven rules are removed from .claude/task-reviewer-rules.md and the rules that remain keep their existing IDs
- [x] #7 Gates: uv run ruff check . is clean, uv run pytest passes, and LC_ALL=C node_modules/.bin/bats tests/unit passes with no new failures relative to master
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: branch task-268 is stacked on task-267 (In Progress, unmerged, awaiting host verification) so the bundle ships 267's amended R5; merge only after task-267 lands. Add plugins/ralph/skills/ralph-init/rules/task-reviewer-rules.infra.md with R-INFRA-1..7 (R3,R4,R5,R6,R8,R10,R15), generic wording (no task IDs, no 'core'/'parity' words); extend the agent loader with INFRA_BUNDLE + infra_rules gate mirroring docs_rules (unset → ralph.sh or scripts/ralph/ralph.sh marker); document it; bats loader tests; python content tests; remove the 7 rules from .claude/task-reviewer-rules.md with an ID map in the preamble; update CLAUDE.md R5 pointer, README, naming-guard comment (live+template).

Commit: `a4e8ac9` - task-268: ship the infrastructure reviewer rules as a plugin bundle gated by infra_rules

Commit: `22c6151` - task-268: pin the infra bundle's rule statements and the project file's ID map

Implemented: rules/task-reviewer-rules.infra.md carries R-INFRA-1..7 (R3→1, R4→2, R5→3 incl. TASK-267's bash 3.2 text, R6→4, R8→5, R10→6, R15→7); generic wording (no task IDs; 'coreutils' reworded to 'userland'; repo-only test_bash32_syntax.py pointer replaced by '/bin/bash -n'). Agent loader refactored into conf_value + shared_tier (same messages for docs, so all prior bats tests pass unchanged except provenance line index + one scoped 'not applied' assertion); infra unset default = ralph.sh or scripts/ralph/ralph.sh exists; new 'infra bundle:' provenance line. Project rules file keeps R7/R11/R12 with stable IDs and a preamble ID map. Also: CLAUDE.md lint pointer, README, naming-guard R5 comment → R-INFRA-3 (live + template, byte-identical).
Verification (container): loader snippet parses and runs under /tmp/bash32 (GNU bash 3.2.57); live run on this repo: 'tier shared infra: loaded (.../task-reviewer-rules.infra.md)', 7 R-INFRA rules, docs not applied. AC2 grep -nE 'parity|stacks|services|channels|core|TASK-[0-9]' over the bundle → no output (also with -i). Gates: ruff clean; pytest 789 passed 1 skipped; bats tests/unit 148 tests, only 'not ok 134 R11: settings.local.json keeps the template's JSON shape' which fails identically on master (#124 of 138; untracked settings.local.json).
DEFERRED (R-INFRA-2 / R4 limit): live check that the installed agent loads the infra bundle, and the updated agent description frontmatter, need merge + plugin update + reload — post-merge host verification.

Commit: `14977c1` - task-268: restore naming-guard.sh's executable bit and cite R-INFRA-3 in the remaining hook comments

Review: ralph:task-reviewer CHANGES REQUESTED (1 blocking: naming-guard.sh lost its 100755 mode via sed -i on the masked .claude mount; 2 minor: remaining hook comments citing R5, bats header wrap) → fixed in 14977c1 → re-review APPROVED (0 blocking, 0 minor, SCORE 10) on git diff task-267..HEAD.
NOT MERGED: task-268 is stacked on task-267, which is In Progress awaiting macOS host verification; merging now would land 267's unverified commits on master. Once task-267 is Done and merged: rebase task-268 onto master (or merge master in), re-run gates, run .claude/hooks/bump-version.sh --auto (shipped plugin files changed → minor bump expected), mark Done, merge --no-ff, bump-version.sh --tag. Then on the host after a plugin update + reload: run the task-reviewer agent in this repo and confirm its provenance shows 'tier shared infra: loaded' (deferred R-INFRA-2 check).

Host gates (macOS, interactive session after the Ralph run, branch merged with master first so it carries TASK-267 Done and the 0.11.2 version): ruff clean; pytest 793 passed 2 skipped; bats tests/unit 148 ok, 0 not ok. The infra bundle carries 7 R-INFRA rules; .claude/task-reviewer-rules.md retains only R7, R11 and R12 with their original IDs. Live-agent check that the installed ralph:task-reviewer loads the infra bundle is deferred until this version is pushed and the plugin updated (R4).

Commit: `ec48618` - task-268: bump plugin version to 0.12.0 (minor)

Post-merge live check (recorded by TASK-270): after the plugin update the installed 0.12.0 agent printed `plugin version: 0.12.0` and `tier shared infra: loaded (/Users/paul/.claude/plugins/cache/dddpaul-ralph/ralph/0.12.0/skills/ralph-init/rules/task-reviewer-rules.infra.md)`; both installed bundles are byte-identical to master.
<!-- SECTION:NOTES:END -->
