---
id: TASK-226
title: Default Ralph and refine model to Opus 5 (claude-opus-5)
status: Done
assignee: []
created_date: '2026-08-19 11:04'
updated_date: '2026-08-19 12:46'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Bump the default --model from claude-opus-4-8 to claude-opus-5 (Opus 5, the latest Opus) across the Ralph orchestrator, the refine orchestrator, and their skill docs, so new runs use Opus 5 without an explicit override.

Direct precedent: TASK-179 did the identical claude-opus-4-7 -> claude-opus-4-8 swap. Read it for the file map and the leave-untouched policy; this task repeats it one model forward.

## Canonical defaults (load-bearing)

Two argparse defaults are the source of truth:

```text
plugins/ralph/skills/ralph-run/scripts/ralph/args.py:82         parser.add_argument("--model", default="claude-opus-4-8")
plugins/ralph/skills/ralph-run/scripts/ralph/refine/args.py:90  parser.add_argument("--model", default="claude-opus-4-8")
```

Their asserted counterparts:

```text
plugins/ralph/skills/ralph-run/tests/test_orchestrator_args.py:78   assert parsed.model == "claude-opus-4-8"
plugins/ralph/skills/ralph-run/tests/test_refine_args.py:150        (same assertion, refine)
```

## Doc surfaces that pin the same string

```text
plugins/ralph/skills/ralph-run/SKILL.md:21     defaults table row  | model | claude-opus-4-8 | --model |
plugins/ralph/skills/ralph-run/SKILL.md:49     divergence note ("... match the orchestrator's own defaults (claude-opus-4-8 and max) ...")
plugins/ralph/skills/ralph-refine/SKILL.md:37  flag table row for model
README.md:146                                  CLI options table row for --model
```

## Consistency sweep (no behavior impact)

Explicit fixture inputs still passing model="claude-opus-4-8" should move too, so no mixed 4-8/5 references remain under plugins/: test_loop_whitelist_summary.py, test_loop_exit_code.py, test_loop_push.py, test_loop_max_iter_summary.py, test_tool_claude.py (input + assertion), test_loop_deltas.py, test_loop_devcontainer_up.py, test_loop_paused_summary.py, test_loop_whitelist_tasks_remaining.py.

## Leave untouched

- Docstring examples that name an older model illustratively, e.g. plugins/ralph/skills/ralph-run/scripts/ralph/tools/claude.py:60 ("e.g. claude-opus-4-7").
- Historical records: everything under design/ and backlog/tasks/ (they document what was true when written).

## Why no other code changes

The exact model id is claude-opus-5 — no date suffix. The repo only forwards --model <id> through to the claude CLI and never sends thinking / effort / sampling request parameters, so the Opus 4.8 -> Opus 5 request-parameter breaking changes do not apply here. This is a pure string swap.

Verified by grep before filing: no .claude/ live copy and no ralph-init template carries a model default, so R11 template parity and the ralph-init Init/Upgrade-Mode parity rule are both non-issues for this task.

## Verification one-liner

After the change this must print nothing:

```bash
grep -rn "claude-opus-4-8" plugins/ README.md
```
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 plugins/ralph/skills/ralph-run/scripts/ralph/args.py --model default is "claude-opus-5"
- [x] #2 plugins/ralph/skills/ralph-run/scripts/ralph/refine/args.py --model default is "claude-opus-5"
- [x] #3 plugins/ralph/skills/ralph-run/SKILL.md defaults table row and divergence note both read claude-opus-5
- [x] #4 plugins/ralph/skills/ralph-refine/SKILL.md flag table model row reads claude-opus-5
- [x] #5 README.md --model CLI options row reads claude-opus-5
- [x] #6 grep -rn "claude-opus-4-8" plugins/ README.md returns no matches
- [x] #7 Docstring example in plugins/ralph/skills/ralph-run/scripts/ralph/tools/claude.py and all files under design/ and backlog/tasks/ are unchanged by this task
- [x] #8 uv run pytest passes
- [x] #9 uv run ruff check . passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Verified claude-opus-5 is a REAL, current model via official docs (platform.claude.com/docs/en/about-claude/models/overview.md) — API id/alias 'claude-opus-5' (dateless pinned snapshot, no date suffix), $5/$25, 1M ctx, 128k out, adaptive thinking, knowledge cutoff May 2026, released ~2026-07-24; now Anthropic's recommended default for agentic coding, with Opus 4.8 moved to Legacy. This is the TASK-179 pattern one model forward. Pure string swap claude-opus-4-8 -> claude-opus-5 across plugins/ + README.md only (2 args.py defaults, ralph-run SKILL.md table+divergence note, ralph-refine SKILL.md flag row, README CLI row, 10 test fixtures/assertions). Leave claude.py:60 docstring (claude-opus-4-7), design/, backlog/tasks/ untouched. Verify grep -rn claude-opus-4-8 plugins/ README.md is empty; run pytest + ruff.

Commit: `09330ed` - task-226: default Ralph and refine model to Opus 5 (claude-opus-5)

Commit: `5d0ccb7` - task-226: restore model-column alignment in ralph-refine SKILL.md table

Done: Swapped default --model claude-opus-4-8 -> claude-opus-5 across plugins/ + README.md (2 argparse defaults, ralph-run SKILL.md table+divergence note, ralph-refine SKILL.md flag row, README CLI row, 10 test fixtures/assertions). claude.py:60 docstring (claude-opus-4-7), design/, backlog/tasks/ left untouched (AC#7). AC#6 grep clean. Verified claude-opus-5 is REAL/current via official Anthropic docs (models/overview.md: API id+alias 'claude-opus-5', dateless pinned snapshot, released ~2026-07-24, recommended default for agentic coding; Opus 4.8 now Legacy) — not a hallucinated id; cached claude-api skill catalog (2026-06-04) and env context simply predate the launch. Gates: uv run pytest 346 passed; uv run ruff check . all passed. task-reviewer verdict APPROVED (R1-R16, no violations). Also restored the ralph-refine model-column table padding the shorter string had unaligned (reviewer's non-blocking nit).

Commit: `7b16b44` - task-226: bump plugin version to 0.3.4 (patch)
<!-- SECTION:NOTES:END -->
