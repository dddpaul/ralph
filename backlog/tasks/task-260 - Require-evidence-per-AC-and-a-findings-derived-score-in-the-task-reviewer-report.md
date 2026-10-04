---
id: TASK-260
title: >-
  Require evidence per AC and a findings-derived score in the task-reviewer
  report
status: To Do
assignee: []
created_date: '2026-10-04 17:33'
updated_date: '2026-10-04 17:57'
labels: []
dependencies:
  - TASK-259
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

task-reviewer's verdict is the only machine check between an implemented task and master, and in practice it approves results that are wrong. On the source machine one documentation project had four consecutive tasks close the same "text fits the box" criterion and get APPROVED, each time on a render that did not prove what the criterion claimed: the reviewer took the author's statement at face value. In two other projects the reviewer recorded no CHANGES REQUESTED across 127 and 144 tasks. The human ended up as the real reviewer, giving repeated rounds of feedback on finished documents.

Where the implementing agent did receive CHANGES REQUESTED, it fixed the work and re-ran the review (41 tasks in one project, one of them approved only on the third round). So the weak point is approval without verification, not an ignored verdict.

The checklist item "Acceptance criteria met — every AC in the task is satisfied by the diff" asks for a judgment but no proof, and the report has no place for one. This repo's own `.claude/task-reviewer-rules.md` R2 ("Every AC must be checked or explicitly deferred") already demands part of this, but it applies only here.

## Scope

In scope:
- Evidence per AC. In the report, every AC the reviewer counts as met is listed with what it checked: a command it ran plus the relevant output lines, a `file:line` quote, or the path of a rendered image or crop for a visual criterion. An AC without evidence is reported as NOT met.
- The reviewer runs the checks itself where it can (tests, grep, build, render). Quoting the task's own notes or the author's summary is not evidence.
- An AC that cannot be verified from inside the review environment (for example, it needs the host) is reported as "not verifiable here" with the reason. It counts as met only if the task notes defer it explicitly with a reason.
- Findings are classified as blocking or minor. Blocking: an AC not met (including missing evidence), a violation of a rule from a loaded rules file, and checklist items on correctness, bugs, security and unintended changes. Minor: style remarks not backed by a rule.
- Violated rules from loaded rules files are named by rule ID in the findings.
- Verdict and score are derived from findings by a fixed rubric written in the agent file, never from overall impression: APPROVED if and only if there are zero blocking findings, with SCORE = 10 minus the number of minor findings, floor 7; any blocking finding means CHANGES REQUESTED with SCORE = 5 minus (blocking findings − 1), floor 1. The report's last line is `SCORE: N`, matching the `^SCORE:\s*(\d+)` contract the refine loop already parses.

Out of scope:
- Any hook or orchestrator change that blocks merging on the verdict. Deliberately not proposed: the verdict is already obeyed, and a script cannot judge whether an approval is correct.
- Rules loading tiers — a separate task this one depends on.
- The ralph-reviewer (cumulative review) agent.
- Removing this repo's R2; if it becomes redundant, say so in the task notes only.

## Files

- `plugins/ralph/agents/task-reviewer.md` (exists) — Instructions step 6, checklist item 1, a new report-format section with the evidence list and the scoring rubric.
- `README.md` (exists) — update the task-reviewer description if it documents the report format.
- a test under `tests/` (to-create) — asserts the evidence requirement, the rubric and the `SCORE:` line contract in the agent file.

## Source

Source: /Users/paul/Private/Alfa/Projects/standard/stacks@4691afcfd3b0
Evidence summarized from the task notes of four downstream documentation projects on the source machine; those repos are not readable from the devcontainer, so the relevant facts are inlined above.

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, build command, or visible behavior — not "works correctly").
3. All dependencies in the task's frontmatter are status=Done.
4. Out-of-scope items are not accidentally pulled in by ambiguous AC.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 task-reviewer.md requires every AC counted as met to carry evidence of one of three kinds (a command run plus its relevant output lines, a file:line quote, a rendered image or crop path) and reports an AC without evidence as NOT met — verified by grep
- [ ] #2 task-reviewer.md states that the reviewer runs checks itself where it can and that quoting the task's own notes or the author's summary is not evidence — verified by grep
- [ ] #3 task-reviewer.md reports an AC that cannot be verified inside the review environment as not verifiable here with a reason, counting it as met only when the task notes defer it explicitly with a reason — verified by grep
- [ ] #4 task-reviewer.md classifies findings as blocking or minor and names violated rules from loaded rules files by rule ID — verified by grep
- [ ] #5 task-reviewer.md defines the rubric: APPROVED iff zero blocking findings with SCORE = 10 minus minor findings (floor 7); any blocking finding gives CHANGES REQUESTED with SCORE = 5 minus (blocking findings - 1) (floor 1); the report's last line is SCORE: N — verified by grep
- [ ] #6 A new test asserts the evidence requirement, the rubric and the last-line SCORE contract in plugins/ralph/agents/task-reviewer.md and fails against master's version of that file (mutation-checked)
- [ ] #7 uv run ruff check . is clean, uv run pytest passes and LC_ALL=C bats tests/unit passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Design provenance (checked before starting, not yet implemented). Source design: stacks design/harness-improvement-brainstorm.md at 4691afc — this task is proposal P1, TASK-259 is P2, and the design's order is P2 then P1, matching the dependency. P1 maps faithfully: evidence per AC with no-evidence-means-not-met (P1.1), a 1-10 score plus named violated rules (P1.2), and no merge-blocking hook — the design argues against one explicitly, because review already runs (47 of core's last 49 tasks) and a script cannot judge whether an approval was correct. The cited commit 4691afc is the one that removed that script from P1.

Correction to the SCORE rationale in this task's description, verified in code. The claim "matching the ^SCORE:\s*(\d+) contract the refine loop already parses" is true as a statement about line syntax and false as a statement about wiring. The regex is at plugins/ralph/skills/ralph-run/scripts/ralph/refine/extract.py:48 and belongs to the refine loop's own author/reviewer roles: refine/roles.py:49-51 (REVIEW_INSTRUCTION) requires both the SCORE line AND <summary>...</summary>, refine/loop.py:304 extracts score and summary from the same call, and extract.summary raises ExtractionError when no <summary> block is present. task-reviewer has no references anywhere under refine/. --reviewer only checks os.access(..., R_OK), so plugins/ralph/agents/task-reviewer.md could be passed manually as a role file, but that is plain role-text reuse, not integration, and it would fail extraction for want of summary tags. Resume reparses its own review-v<n>.md outputs (loop.py:431-432), not branch-review reports. Keep the SCORE line; describe it as the same line syntax refine uses, with no automatic refine consumer for task-reviewer reports today. No orchestrator change is needed or proposed.

R4 limit (this repo's own reviewer rules). Both this task and TASK-259 edit plugins/ralph/agents/task-reviewer.md, and the Agent enum is fixed at session start, so neither can demonstrate live agent behaviour. This task's entire deliverable is agent behaviour and its ACs verify it statically (greps plus a mutation-checked test). The first genuine exercise of the new rubric is the next task reviewed in a fresh session, and this task's own review runs under the pre-change rules. That is inherent, not a defect in the ACs, but it must not be reported as behavioural verification.

How the result can and cannot be checked. Nothing in Ralph records review verdicts: summary.py RunSummary carries exit_reason, tasks_completed, tasks_remaining, iterations_used, max_iterations, failed_iterations, wall_time_sec and iter_durations_sec with no verdict field, failed_iterations counts tool failures rather than review refusals, and loop.py:574 _truncate_run_log zeroes the run log at every startup so it is not a history. The ACs here verify the mechanism exists; they cannot show a reviewer began refusing bad work. The design's own measures are downstream and after the fact — for P1, CHANGES REQUESTED appearing in core and channels plus fewer rounds of human remarks — against this baseline: stacks 353 tasks / 41 refusals / 94 rule lines; services 90 / 18 / 160; channels 144 / 4 (and those four are rule text quoted in task descriptions, not refusals) / 38; core 127 / 0 / 26. The falsifiable predictions are channels 0 -> >0 and core 0 -> >0 after they upgrade. Counting substrings over task notes would reproduce exactly the channels false positives above; honest measurement needs real review events (project, task, reviewed commit, round, rules version, verdict, findings) plus later human-correction rounds on the same artifact, compared across comparable pre/post work, and must not optimise for refusal count alone since false refusals are also a cost. This repo could host such a collector; it cannot prove the outcome with its own unit tests.

P3 (frozen examples) remains outstanding, channels first per the design. It is load-bearing for the design's larger claim — the design states P1's limit as "доказательство ловит непроверенное, но не неверно проверенное", and in services the slide crop existed but was rendered with the wrong fonts. R-DOCS-6's fc-match step covers that specific failure mode; R-DOCS-4/5 check internal consistency, whereas frozen expectations provide an independent oracle. The design schedules P3 third, so it does not block this task, but shipping 259+260 must not be reported as demonstrating the whole outcome.
<!-- SECTION:NOTES:END -->
