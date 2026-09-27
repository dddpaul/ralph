---
id: TASK-253
title: Enforce the documented line length and formatting in the lint gate
status: To Do
assignee: []
created_date: '2026-09-27 17:01'
labels: []
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

CLAUDE.md's Code Style section states two rules that nothing enforces:

> Formatting: Follow PEP 8, use ruff formatter
> Line length: Maximum 88 characters

`pyproject.toml` sets `line-length = 88`, but that value is only honoured by `ruff format`. `ruff check` never tests it, because the line-length rule is `E501` and the lint selection is:

```toml
extend-select = ["I", "B", "UP", "SIM"]
```

`E501` is in neither that list nor ruff's default rule set, so `uv run ruff check .` — the project's documented Lint command — passes on a 103-character line. Measured on master at v0.7.0:

- **26 lines over 88 characters**, across 12+ files, including shipped orchestrator code (`plugins/ralph/skills/ralph-run/scripts/ralph/loop.py`) and `tests/scripts/check_run_clean.py`.
- **`uv run ruff format --check .` reports 36 of 76 files would be reformatted.**

This was found when a review caught a 103-character comment line that the lint gate had just passed as clean. The gate was not wrong — it genuinely does not check this — which is the problem: a reviewer or a human has to catch by eye what the documented rule says is mechanical.

## Direction

Make the two stated rules actually enforced, so a violation fails `uv run ruff check .` (or a formatting gate) rather than relying on review.

Decide and record which of these the project wants, since they overlap:

1. **Add `E501` to `extend-select`** — makes over-long lines a lint failure. Requires fixing the 26 existing lines first, which is mechanical but touches shipped code.
2. **Add a `ruff format --check` gate** — subsumes line length for code (the formatter wraps), but not for comments and strings, which it leaves alone. Requires reformatting the 36 files first.

They are complementary rather than alternatives: the formatter re-wraps code, `E501` is what catches a long comment or string literal — which is exactly the case that slipped through. Doing both is the only combination that makes the CLAUDE.md sentence true.

## Scope note

The mechanical reformat is the bulk of the diff and is low-risk (the suite covers it), but it is large and touches files unrelated to any feature. Keep it in its own commit, separate from the config change, so the config change stays reviewable. Update the CLAUDE.md / README Lint line if the gate command changes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A line longer than 88 characters fails the project's documented lint command, demonstrated by adding one temporarily and observing the failure
- [ ] #2 A file that ruff format would change fails a gate, or the decision not to gate formatting is recorded with its reason
- [ ] #3 The 26 existing over-limit lines are brought under 88 characters, including the shipped orchestrator code
- [ ] #4 The mechanical reformat is a separate commit from the configuration change
- [ ] #5 CLAUDE.md and README state the lint command that actually enforces these rules
- [ ] #6 uv run pytest passes after the reformat with no behaviour change
- [ ] #7 LC_ALL=C bats tests/unit and bats tests/integration pass with no new failures
<!-- AC:END -->
