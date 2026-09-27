---
id: TASK-253
title: Fail the lint gate on Python lines over 120 characters
status: Done
assignee: []
created_date: '2026-09-27 17:01'
updated_date: '2026-09-27 19:03'
labels: []
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

CLAUDE.md's Code Style section states a rule that nothing enforces:

> Line length: Maximum 88 characters

`pyproject.toml` sets `line-length = 88`, but that value is only honoured by `ruff format`. `ruff check` never tests it, because the line-length rule is `E501` and the lint selection is:

```toml
extend-select = ["I", "B", "UP", "SIM"]
```

`E501` is in neither that list nor ruff's default rule set, so `uv run ruff check .` — the project's documented Lint command — passes on a 103-character line. This was found when a review caught exactly such a line that the lint gate had just reported clean. The gate was not wrong; it genuinely does not check this, which is the problem: a reviewer or a human has to catch by eye what the documented rule says is mechanical.

## Decisions (recorded 2026-09-27)

- **Code only, 120 characters.** 88 was aspirational and unenforced; 120 is the limit the project actually wants.
- **Documentation lines stay unrestricted.** This needs no work: ruff only reads `.py`, and there is no markdownlint or `.mdlrc` anywhere in the repo. Do not add one.
- **`ruff format` is not gated, and keeps its 88-character wrap target.** Gating it would reformat 35 files for no functional reason, and raising the formatter's own limit to 120 is actively worse — the formatter *rejoins* short lines up to the limit, so `ruff format --check --line-length 120 .` reports **59** files instead of 35, collapsing code that was deliberately wrapped.

## Direction

Keep `line-length = 88` as the formatter's target and give the lint rule its own, higher ceiling — ruff's idiom for "wrap at 88 by habit, fail past 120":

```toml
[tool.ruff]
line-length = 88                      # formatter's wrap target (not gated)

[tool.ruff.lint]
extend-select = ["I", "B", "UP", "SIM", "E501"]

[tool.ruff.lint.pycodestyle]
max-line-length = 120                 # what actually fails the gate
```

Measured on master at v0.8.0: **zero** Python lines exceed 120 (`git ls-files '*.py' | xargs awk 'length > 120'`), so no cleanup is needed and no shipped code has to be touched. The above was verified to pass `ruff check` on master and to flag a synthetic 147-character line.

## The one real cost

`lint.pycodestyle.max-line-length` also feeds SIM108's "would the suggested ternary fit on one line?" test, so raising it to 120 surfaces three previously-suppressed SIM108 findings:

```text
plugins/ralph/skills/ralph-run/scripts/ralph/preflight.py:337
plugins/ralph/skills/ralph-run/tests/test_tasks.py:59
scripts/shorten-backlog-filenames.py:722
```

Each is a mechanical `if`/`else` → ternary rewrite. Apply them, or add a narrow ignore with a recorded reason — but do not leave the gate red.

## Doc updates

Two independent files state the old number:

- `CLAUDE.md` (Code Style, in `## Project-Specific`)
- `plugins/ralph/skills/ralph-init/templates/root/CLAUDE.conventions.python.md`

The template fragment is registered in `non_mirrored_templates` in `tests/unit/template-parity.bats`, so this is **not** an R11 parity pair — they are two deliberate edits. The fragment is composed into `CLAUDE.md` at init and is not re-synced on upgrade, so that edit only reaches newly initialized projects; no ralph-init Upgrade Mode change is required.

The PRD and brainstorm documents under `design/` mention `line-length = 88` as design history — leave them alone.

## Out of scope

- Gating `ruff format` (decided against above; record the decision, do not implement it).
- Any line-length rule for markdown, or adding a markdown linter.
- Reformatting to 88, or changing the formatter's wrap target.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A Python line longer than 120 characters fails uv run ruff check ., demonstrated by adding one temporarily and observing the failure
- [x] #2 No Python line is rewrapped for length: E501 reports zero findings on the repo as it stands, so the change touches no shipped code for line length
- [x] #3 The three SIM108 findings unlocked by the raised pycodestyle limit are fixed, or narrowly ignored with the reason recorded in pyproject.toml
- [x] #4 ruff format keeps line-length 88 and is not added as a gate, with the reason recorded in pyproject.toml or the task notes
- [x] #5 CLAUDE.md and templates/root/CLAUDE.conventions.python.md state the 120-character limit and scope it to code, not markdown
- [x] #6 No markdownlint config or markdown line-length rule is added anywhere in the repo
- [x] #7 uv run pytest, LC_ALL=C bats tests/unit and bats tests/integration pass with no new failures
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: add E501 with pycodestyle max-line-length=120 in pyproject (formatter stays 88, ungated, reason commented); rewrite the 3 SIM108 sites as ternaries; update CLAUDE.md + python conventions template; verify with a synthetic long line.

Commit: `03552d5` - task-253: fail ruff check on Python lines over 120 characters

Verified: synthetic 146-char line -> E501, rc=1; E501 zero findings on repo; SIM108 x3 rewritten as parenthesized ternaries (formatter-clean; the 3 files' pre-existing ruff-format drift is byte-identical to master). ruff format stays at 88 and ungated, reason commented in pyproject.toml. No markdownlint config exists. pytest 669 passed; bats unit 110 (only #96 R11 settings.local.json fails, pre-existing on master); integration 52/52.

task-reviewer: APPROVED.

Commit: `d32731b` - task-253: bump plugin version to 0.8.1 (patch)
<!-- SECTION:NOTES:END -->
