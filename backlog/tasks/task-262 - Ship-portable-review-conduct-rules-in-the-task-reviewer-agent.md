---
id: TASK-262
title: Ship portable review-conduct rules in the task-reviewer agent
status: Done
assignee: []
created_date: '2026-10-04 18:53'
updated_date: '2026-10-05 05:58'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Default code review rules already ship — they live in the `task-reviewer` agent, not in a rules file: the 8-item checklist plus the Evidence per AC, Findings Classification, Verdict and Score Rubric and Report Format sections added by TASK-260. For a fresh Code project all three rule-file tiers are empty by design: the user-global file is the reviewer's own and is not shipped, the shared docs tier is skipped when there is no Obsidian vault, and ralph-init never creates the project file.

The agent is the right home for portable rules because it has no installation chain. Plugin-bundled agents are distributed with the plugin rather than copied per project — `tests/unit/template-parity.bats` asserts exactly that ("plugin-bundled agents are distributed, not mirrored") — so a rule added here reaches every project on the next plugin update, with no `ralph-init upgrade`, no per-project write and no prose step for an agent to misexecute. A managed rules file reaches a project only if someone runs the upgrade there.

Six of this repository's 17 project rules are review *conduct*: they describe how to review rather than what this repo contains, so they are portable as written and cost nothing to ship.

- R1 and R9 — review the diff, not the working tree; git is the truth
- R2 — every AC must be checked or explicitly deferred (complements TASK-260's evidence rule, which covers evidence but not the bookkeeping)
- R13 — rationalization is not exemption
- R14 — content preservation during moves
- R16 — task descriptions must not reference brainstorm files
- R17 — a changed external-tool default needs an invocation AC

R16 and R17 are the urgent pair, because the plugin already ships their producer halves while shipping no enforcement. `plugins/ralph/skills/ralph-task/SKILL.md:144` tells every project that its MUST rule 4 "is enforced post-merge as `task-reviewer` rule R16" — true in this repository only. The decomposition heuristic's rule 5 in the same file demands an invocation AC for a changed external-tool default, which is R17, equally unenforced downstream.

Four shipped citations point at rules no downstream project has. Resolve each:

- `plugins/ralph/skills/ralph-task/SKILL.md:144` cites R16 — becomes true once R16 ships in the agent
- `plugins/ralph/skills/ralph-init/SKILL.md:320` and `:501` cite R6 — R6 is infrastructure, not conduct, and is out of scope here; reword these to state the reason (a bare `*` crosses `/` and auto-allows bash over every cached plugin file) without depending on a rule ID the reader does not have
- `plugins/ralph/skills/ralph-task/SKILL.md:98` and `plugins/ralph/skills/ralph-stop/SKILL.md:40` cite R11 — R11 is template parity, meaningful only in this repository. It must NOT ship. Rewrite both to describe the mirror concept without the ID

Keep the project file authoritative for what stays. R11 remains project-only. R7 (no AI-attribution trailers) is project policy, not a default — this repo forbids them, other projects legitimately want them — so it stays project-only too. R3, R4, R5, R6, R8, R10 and R15 are ralph-init infrastructure rules and belong to the separate managed-tier task, not here.

Avoid duplication: a rule moved into the agent must be removed from `.claude/task-reviewer-rules.md`, or the reviewer loads it twice. The upgrade flow already prints a hint for exactly this shape of duplication between the project file and a managed file, so leaving both in place contradicts a check the plugin ships.

Verification constraint. The `ralph:task-reviewer` agent runs from the installed plugin cache, not from this worktree, so edits here are not live until the plugin is reinstalled or updated. Per project rule R4 the Agent enum is also fixed at session start. Verify the ACs statically — greps plus a test — and do not claim behavioural verification of the new rules in the implementing session.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 plugins/ralph/agents/task-reviewer.md states the six conduct rules — review the diff not the working tree, every AC checked or explicitly deferred, rationalization is not exemption, content preservation during moves, no brainstorm-file references in task descriptions, and an invocation AC for a changed external-tool default — verified by grep for each
- [x] #2 The agent does not ship R11 template parity or R7 AI-attribution policy: grep over plugins/ralph/agents/task-reviewer.md finds no template-parity rule and no commit-trailer rule
- [x] #3 plugins/ralph/skills/ralph-task/SKILL.md line 144's claim that the brainstorm-reference rule is enforced post-merge by the reviewer is now true, because the agent carries that rule
- [x] #4 No shipped file under plugins/ cites a project rule ID that downstream projects lack: grep for R6, R11 and R16 over plugins/ returns only citations that the agent itself now carries, with the R6 and R11 mentions reworded to describe the reason instead of the ID
- [x] #5 Every conduct rule added to the agent is removed from .claude/task-reviewer-rules.md, so no heading appears in both — verified by comparing the '## ' headings of the project file against the agent's rule statements
- [x] #6 The remaining project file still carries R11, R7 and the ralph-init infrastructure rules, and its rule numbering is left coherent after the removals
- [x] #7 A test pins the agent's conduct rules against removal, and it fails if any one of the six statements is deleted from the agent file — record the observed mutation results in the task notes
- [x] #8 Gates: uv run ruff check . is clean, uv run pytest passes, and LC_ALL=C node_modules/.bin/bats tests/unit passes with no new failures relative to master
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Commit: `e26e7c2` - task-262: ship six review-conduct rules as built-in R-CORE rules in the task-reviewer agent

Plan: add a Built-in Rules section (R-CORE-1..6) to plugins/ralph/agents/task-reviewer.md carrying R1+R9, R2, R13, R14, R16, R17 generalized for any project; drop those sections from .claude/task-reviewer-rules.md with a retired-ID map; reword shipped R6/R11/R16 citations; pin with tests/python/test_task_reviewer_core_rules.py.

Mutation results (tests/python/test_task_reviewer_core_rules.py, 12 tests): deleting the whole ### R-CORE-N subsection from the agent -> R-CORE-1: 1 failed/11 passed; R-CORE-2: 1 failed; R-CORE-3: 1 failed; R-CORE-4: 1 failed; R-CORE-5: 2 failed (statement + scan); R-CORE-6: 1 failed. Deleting only the sentence 'A silent unchecked AC is a blocking finding.' -> 1 failed. Agent restored byte-identical after each run.
Gates: uv run ruff check . clean; uv run pytest 719 passed; LC_ALL=C node_modules/.bin/bats tests/unit 1..119 with one failure, #104 'R11: settings.local.json keeps the template's JSON shape', which fails identically on master (verified with the change stashed) - no new failures.
Verification is static only: the ralph:task-reviewer agent runs from the installed plugin cache, so the new R-CORE rules are not live in this session; behavioural verification is deferred to the first review after a plugin update.
Decisions: built-in rules use the R-CORE-N namespace (like R-DOCS-N) so they cannot collide with a downstream project's own R-numbered rules; R1 and R9 merged into R-CORE-1. Project file keeps R3-R8, R10-R12, R15 with their IDs (cited by notes, CLAUDE.md and docs); retired IDs mapped in the preamble instead of renumbering. ralph-task line 144 now cites R-CORE-5 and says the rule is enforced at review time, before merge (the old 'post-merge' was inaccurate). R12 was not listed in the task and stays project-only.

Commit: `4b11e68` - task-262: say the three loading tiers are rules files, not all rules

task-reviewer (ralph:task-reviewer) APPROVED, SCORE 9: 0 blocking, 1 minor (agent line 13 said 'Rules come in three tiers' though built-ins are a fourth, more general tier) - fixed to 'Rules files come in three tiers'. Final gates: ruff clean, pytest 719 passed, bats only pre-existing #104.

Commit: `04ee088` - task-262: bump plugin version to 0.9.3 (patch)
<!-- SECTION:NOTES:END -->
