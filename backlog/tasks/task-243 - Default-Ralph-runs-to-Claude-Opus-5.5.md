---
id: TASK-243
title: Default Ralph runs to Claude Opus 5.5
status: Done
assignee: []
created_date: '2026-09-27 11:08'
updated_date: '2026-09-27 11:42'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Anthropic released Claude Opus 5.5 on 2026-09-22. It performs at Claude Fable 5.1 level on most
agentic coding work while costing less per token than Opus 5 ($4/$20 vs $5/$25 per MTok) and
generating output ~30% faster. Ralph loops are long-running and token-heavy, so the default model
is where this saving compounds most. Ralph currently defaults to `claude-opus-5`, so every run
pays the older rate unless the operator remembers `--model`.

## Scope

In scope:
- Bump the orchestrator's `--model` argparse default to `claude-opus-5-5`.
- Bump the refine loop's `--model` argparse default to `claude-opus-5-5`.
- Update the two tests that assert the default string.
- Update the three docs that publish the default (ralph-run SKILL.md table + prose, ralph-refine SKILL.md flag row at line ~37, README flag table).

Out of scope:
- `scripts/shorten-backlog-filenames.py` (`DEFAULT_MODEL = "haiku"`) — deliberately a fast/cheap
  model for slug generation. Do NOT change.
- `design/*.md` brainstorm and PRD documents — historical records; do not rewrite.
- Test fixtures that pass `model="claude-opus-5"` explicitly (test_loop_*.py, test_tool_claude.py):
  they supply an explicit model rather than exercising the default, so they are not part of this change.
- `scripts/ralph/tools/claude.py` docstring example — an illustrative value, not a default.
- The `effort` default stays `medium`. Do not touch it.

## Files

- `plugins/ralph/skills/ralph-run/scripts/ralph/args.py` (exists) — line ~83, `parser.add_argument("--model", default="claude-opus-5")`; the orchestrator's own default.
- `plugins/ralph/skills/ralph-run/scripts/ralph/refine/args.py` (exists) — line ~90, same pattern for the refine loop.
- `plugins/ralph/skills/ralph-run/tests/test_orchestrator_args.py` (exists) — line ~78, `assert parsed.model == "claude-opus-5"`.
- `plugins/ralph/skills/ralph-run/tests/test_refine_args.py` (exists) — line ~150, same assertion.
- `plugins/ralph/skills/ralph-run/SKILL.md` (exists) — line ~21 defaults table row `| model | claude-opus-5 | --model |` and line ~52 prose naming the orchestrator defaults.
- `README.md` (exists) — line ~152 flag table, `| \`--model <model_id>\` | Model ID for Claude Code | \`claude-opus-5\` |`.

## Source

Source: /Users/paul/.claude@143e716c7589-dirty
Source design doc (read-only context, do NOT modify): none — this handoff originated from a
Claude Code session that verified Opus 5.5's model ID and pricing against
https://platform.claude.com/docs/en/about-claude/models/overview

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
- [x] #1 grep -n "default=\"claude-opus-5-5\"" plugins/ralph/skills/ralph-run/scripts/ralph/args.py returns the --model line
- [x] #2 grep -n "default=\"claude-opus-5-5\"" plugins/ralph/skills/ralph-run/scripts/ralph/refine/args.py returns the --model line
- [x] #3 plugins/ralph/skills/ralph-run/tests/test_orchestrator_args.py asserts parsed.model == "claude-opus-5-5"
- [x] #4 plugins/ralph/skills/ralph-run/tests/test_refine_args.py asserts parsed.model == "claude-opus-5-5"
- [x] #5 plugins/ralph/skills/ralph-run/SKILL.md defaults table row and surrounding prose both read claude-opus-5-5
- [x] #6 README.md --model flag table row shows claude-opus-5-5 as the default
- [x] #7 uv run pytest passes and uv run ruff check . reports no new findings
- [x] #8 grep -n "claude-opus-5-5" plugins/ralph/skills/ralph-refine/SKILL.md returns the model row of the defaults table, and no claude-opus-5 default remains in that file
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Verified against live Anthropic docs (platform.claude.com/docs/en/about-claude/models/overview.md) that claude-opus-5-5 is REAL and current — Claude Opus 5.5, API id + alias 'claude-opus-5-5' (dateless pinned snapshot), $4/$20 per MTok, 1M ctx, 128k out, adaptive thinking, default effort medium, knowledge cutoff Jun 2026, retirement not sooner than 2027-09-22; it is now the recommended default for most workloads and claude-opus-5 has moved to Legacy. The handoff premises (release 2026-09-22, $4/$20 vs $5/$25) check out. This is the TASK-226 pattern one model forward: a pure string swap, since the repo only forwards --model <id> to the claude CLI and never sends thinking/effort/sampling request params. Change exactly 6 files: 2 argparse defaults (scripts/ralph/args.py:83, scripts/ralph/refine/args.py:90), 2 default-assertions (tests/test_orchestrator_args.py:78, tests/test_refine_args.py:150), ralph-run SKILL.md table row :21 + prose :52, ralph-refine SKILL.md flag row :37 (preserving the markdown column padding — dropping 2 spaces offsets the 2 added chars, so width stays 17), README.md:152 flag table. Leave untouched per Out of scope: the 10 explicit model= test fixtures (test_loop_*.py, test_tool_claude.py, test_devcontainer_rebuild.py), scripts/shorten-backlog-filenames.py (haiku), claude.py docstring, design/, backlog/tasks/, and the effort=medium default. No ralph-init template mirror needed (R11) — grep shows no claude-opus-5 under templates/. Verify: greps for AC 1-6/8, grep -rn 'claude-opus-5' plugins/ README.md shows only -5-5 plus the deliberate explicit fixtures, then uv run pytest + uv run ruff check .

Commit: `ac3ea4e` - task-243: default Ralph and refine model to Opus 5.5 (claude-opus-5-5)

Commit: `dcd3a1f` - task-243: restore the ralph-refine defaults-table column padding

Done: Swapped the default --model claude-opus-5 -> claude-opus-5-5 across the 6 files named in the task (2 argparse defaults at scripts/ralph/args.py:83 and scripts/ralph/refine/args.py:90, the 2 default-asserting tests, ralph-run SKILL.md table row :21 + divergence prose :52, ralph-refine SKILL.md flag row :37, README.md:152). Model id verified REAL and current against live Anthropic docs, not the cached catalog: Claude Opus 5.5, API id + alias 'claude-opus-5-5', $4/$20 per MTok (vs Opus 5's $5/$25), 1M ctx, 128k out, adaptive thinking, default effort medium, knowledge cutoff Jun 2026, retirement not sooner than 2027-09-22; it is now the recommended default for most workloads and claude-opus-5 has moved to Legacy. Pure string swap — the repo only forwards --model <id> to the claude CLI. All Out-of-scope items left untouched: the 12 explicit model="claude-opus-5" fixture lines (test_loop_*.py, test_tool_claude.py, test_devcontainer_rebuild.py), shorten-backlog-filenames.py's haiku default, the claude.py docstring, design/, and every effort=medium default. R11 template parity not triggered — grep finds no 'opus' under ralph-init/templates/, plugins/ralph/agents/, ralph.sh or refine.sh, since the shims pass --model through without embedding a default. Correction to the Plan note: the ralph-refine defaults column is 18 chars wide, not 17, so the two added characters needed BOTH trailing spaces dropped; the first edit left one behind and made the row 19. Fixed in a follow-up commit — all 20 rows of that table now measure 18. Gates: uv run pytest 498 passed; uv run ruff check . all checks passed (both re-run after the padding fix). task-reviewer verdict APPROVED (R1-R16, no violations; its one blocking-free nit was the padding, now resolved).

Commit: `1e03438` - task-243: bump plugin version to 0.6.4 (patch)
<!-- SECTION:NOTES:END -->
