---
id: TASK-249
title: Require an invocation AC when a task changes an external-tool default
status: Done
assignee: []
created_date: '2026-09-27 13:21'
updated_date: '2026-09-27 14:22'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

TASK-243 changed the orchestrator's `--model` default from `claude-opus-5` to `claude-opus-5-5`. It passed **8 of 8 acceptance criteria** — and every Ralph run then failed 12 seconds after launch:

```
[claude-code:unrecognized_model] {"model":"claude-opus-5-5","query_source":"sdk"}
API Error: 400 Claude Code 2.1.259 does not support this model; version 2.1.280 or newer is required.
```

The model id was correct and the price was correct; the *client* could not use it. Zero of four queued tasks ran.

Every one of those 8 ACs was a static assertion — greps for the new string in two argparse defaults, two unit tests asserting the parsed default, three doc tables, plus lint and test gates. Not one of them launched the tool with the new value. A default that feeds an external program is only meaningfully verified by running that program, because the failure modes live outside this repo: the tool may reject the value, require a newer version, need different auth, or accept it and behave differently.

This is a recurring shape, not a one-off. The same gap was caught *before* running on two earlier tasks in the same series (a task adding bats tests while gating only on pytest, twice), which is what makes it worth encoding rather than remembering.

## Where the check belongs

Three gates a change like this passes through, and it slipped all three:

1. **Review** — `.claude/task-reviewer-rules.md` as a new rule R17. This is the control that demonstrably works in this repo: the reviewer caught real defects in the three tasks either side of 243. It is a registered non-mirror (see the `non_mirrored_templates` list in `tests/unit/template-parity.bats`), so adding a rule here carries **no** R11 parity obligation.
2. **Handoff acceptance** — the "Before starting" checklist in the `## Handoff Inbox` section of `CLAUDE.md`. TASK-243 arrived as a handoff, so its ACs were authored in another project; this gate is the only place this repo can vet them. Its current item 2 asks whether each AC is objectively pass/fail — 243's were, which is exactly why "objectively pass/fail" is insufficient on its own.
3. **Create time** — the verification rule in the 6-rule heuristic in `plugins/ralph/skills/ralph-task/SKILL.md`, so locally-created tasks get the AC from the start.

## Parity

`## Handoff Inbox` is inside CLAUDE.md's mirrored generic region (it sits above `## Project-Specific` in both the live file and `plugins/ralph/skills/ralph-init/templates/root/CLAUDE.md`), so the checklist edit MUST be mirrored there and the region-parity test must still pass. Changing the ralph-task skill is a shipped-file change, so the version bump applies.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 task-reviewer-rules.md gains rule R17 requiring that a diff changing a default passed to an external tool carry at least one AC that invokes the tool with the new value and records the observed result
- [x] #2 R17 states explicitly that static assertions (greps, doc tables, unit tests on the parsed default) are necessary but not sufficient, because they cannot detect that the tool rejects the value
- [x] #3 R17 lists the triggering cases: CLI flag defaults, model ids, image tags, and version pins
- [x] #4 R17 cites the TASK-243 incident with its concrete outcome (8/8 ACs passed, every run failed on a client version floor)
- [x] #5 The Handoff Inbox 'Before starting' checklist in CLAUDE.md gains a matching item, distinguishing it from the existing objectively-pass/fail item
- [x] #6 The same checklist item is mirrored into the ralph-init template CLAUDE.md and the R11 CLAUDE.md region-parity test passes
- [x] #7 The ralph-task skill's verification guidance names the requirement so locally-created tasks get the AC at creation time
- [x] #8 task-reviewer-rules.md remains a registered non-mirror with no new template added for it, and LC_ALL=C bats tests/unit plus uv run pytest and uv run ruff check . all pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: add R17 to .claude/task-reviewer-rules.md (external-tool default needs an invocation AC; static checks insufficient; triggers; TASK-243 incident); add a checklist item under Handoff Inbox in CLAUDE.md + ralph-init template; extend ralph-task rule 5 (table + edit-deliberation bullet); run bats/pytest/ruff; bump version.

Commit: `57f3d5a` - task-249: require an invocation AC when a task changes an external-tool default

Added R17 to .claude/task-reviewer-rules.md (plus R13 range R1–R14 → R1–R17); a Handoff Inbox checklist item in CLAUDE.md, mirrored to the ralph-init template CLAUDE.md; external-tool-default guidance in the ralph-task rule 5 table row and edit-deliberation bullet. Gates: pytest 598 passed, ruff clean, bats tests/unit 110/110 in a clean worktree (in /workspace the settings.local.json shape test fails identically on master because it reads a gitignored local file). task-reviewer: APPROVED.

Commit: `d56f262` - task-249: bump plugin version to 0.6.7 (patch)
<!-- SECTION:NOTES:END -->
