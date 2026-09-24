---
id: TASK-238
title: Default ralph-run effort to medium
status: Done
assignee: []
created_date: '2026-09-24 16:17'
updated_date: '2026-09-24 16:30'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Lower the ralph-run default thinking effort from `max` to `medium`. Requested directly by the user: max-effort iterations are slow and expensive, and medium is the better everyday default; per-invocation overrides (`--effort high`, `/ralph-run effort=max`) stay available.

Scope covers BOTH the skill knob and the orchestrator CLI default, because the ralph-run SKILL.md explicitly documents them as matching — changing only one would introduce new drift.

Current state (verified):

```
plugins/ralph/skills/ralph-run/scripts/ralph/args.py:84
    parser.add_argument("--effort", default="max")

plugins/ralph/skills/ralph-run/SKILL.md:22
    | effort | max | --effort |

plugins/ralph/skills/ralph-run/tests/test_orchestrator_args.py:79
    assert parsed.effort == "max"
```

SKILL.md also carries two prose claims that must stay consistent: line 49 justifies the 60m timeout with "max-effort iterations take longer", and line 52 states "The `model` and `effort` defaults match the orchestrator's own defaults (`claude-opus-5` and `max`)". Both need rewording once the default is `medium` — keep the timeout at 60 (it is still the skill default) but stop attributing it to max effort.

Pre-existing drift this closes: README.md line 149 already documents the `--effort` default as `medium` while the code defaulted to `max`. After this change the README becomes accurate; verify rather than edit it.

Out of scope: `scripts/ralph/refine/args.py` already defaults to `medium` (ralph-refine is a separate sibling) — do not touch it. Tests that pass `effort="max"` as an explicit constructor argument are testing explicit values, not the default, and should stay unchanged.

Governance: this touches shipped `plugins/ralph/**`, so the merge will trigger `bump-version.sh --auto`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 plugins/ralph/skills/ralph-run/scripts/ralph/args.py parses --effort with default 'medium' (grep confirms default="medium", no remaining default="max")
- [x] #2 The ralph-run SKILL.md knob table row reads '| effort | medium | --effort |'
- [x] #3 The SKILL.md defaults note no longer claims the effort default is max: the 60m timeout rationale is reworded without attributing it to max effort, and the 'defaults match the orchestrator' sentence names medium
- [x] #4 tests/test_orchestrator_args.py asserts parsed.effort == 'medium'; tests passing effort explicitly as a constructor argument are left unchanged
- [x] #5 README.md line documenting the --effort default still reads 'medium' and now matches the code (verified, not edited)
- [x] #6 scripts/ralph/refine/args.py is untouched and still defaults to medium
- [x] #7 uv run pytest and uv run ruff check . pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: flip --effort default max->medium in plugins/ralph/skills/ralph-run/scripts/ralph/args.py; update SKILL.md knob table row (line 22), reword the 60m-timeout rationale (line 49) to drop the max-effort attribution, and the defaults-match sentence (line 52) to name medium; update test_orchestrator_args.py default assertion to 'medium'. Leave refine/args.py, README.md line 149 (already medium), and explicit effort="max" constructor args in loop/tool tests unchanged. No R11 template pair covers these files. Gate: uv run pytest && uv run ruff check .

Commit: `f22e62b` - task-238: default ralph-run thinking effort to medium

Done. Flipped the ralph-run orchestrator --effort default from max to medium (plugins/ralph/skills/ralph-run/scripts/ralph/args.py), updated the SKILL.md knob table row, dropped the max-effort attribution from the 60m timeout rationale (now: interactive runs target whole backlog tasks), and named medium in the defaults-match sentence; test_orchestrator_args.py default assertion updated. README.md line 149 already said medium and is now accurate (verified, not edited); refine/args.py untouched. No R11 template pair covers these files. Gate: uv run pytest 498 passed, uv run ruff check . clean. Review: the task-reviewer agent type is UNREGISTERED in this session, so a claude agent carrying the plugins/ralph/agents/task-reviewer.md charter + .claude/task-reviewer-rules.md ran the review -> APPROVED (non-blocking note: tools/claude.py:61 docstring still uses "max" as an example value, not a default claim).

Commit: `8c76b58` - task-238: bump plugin version to 0.5.1 (patch)
<!-- SECTION:NOTES:END -->
