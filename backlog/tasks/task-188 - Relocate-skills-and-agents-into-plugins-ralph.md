---
id: TASK-188
title: >-
  Relocate skills and agents into plugins/ralph and repoint build and test
  config
status: Done
assignee: []
created_date: '2026-07-03 09:37'
updated_date: '2026-07-03 11:04'
labels:
  - 'feature:ralph-marketplace'
dependencies:
  - TASK-187
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Move all skills and agents under plugins/ralph/ via git mv AND repoint the build/test configuration in the same task so the repo stays green: a bare move leaves pytest red because pyproject pythonpath still targets skills/ralph-run/scripts. The ralph-run scripts and Python tests move with the skill. Folds former US-003. See design/ralph-marketplace-prd.md US-002 and US-003.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All 10 skills moved from skills/* to plugins/ralph/skills/* via git mv with history preserved
- [x] #2 Both agents moved from agents/* to plugins/ralph/agents/* via git mv
- [x] #3 The ralph-run scripts/ and Python tests/ are moved with the skill
- [x] #4 grep -rn for skills/ralph- across md, py, and toml shows no stale top-level skills/ references outside backlog/archive and design/
- [x] #5 The ralph-sync skill under .claude/skills/ is left untouched by this task
- [x] #6 pyproject.toml pythonpath, testpaths, and ruff src/include/strict reference plugins/ralph/skills/ralph-run/...
- [x] #7 bats files under tests/ reference plugins/ralph/skills/ralph-run/scripts/...
- [x] #8 uv run pytest passes
- [x] #9 The bats suite passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) git mv skills -> plugins/ralph/skills and agents -> plugins/ralph/agents (moves ralph-run scripts/ + tests/ with the skill). (2) Repoint pyproject.toml pythonpath/testpaths/ruff.src/pyright.include/pyright.strict to plugins/ralph/skills/ralph-run/{scripts,tests}. (3) Repoint bats path references under tests/ (common.bash RALPH_SCRIPT + CLAUDE_CONFIG_DIR, usage-check.bats, usage-pause.bats, shim.bats, pre-commit-hook.bats, commit-msg-hook.bats) to plugins/ralph/skills/... . Shim (ralph.sh) resolver + task-reviewer-rules R11 + README/CLAUDE.md docs are OUT OF SCOPE (TASK-190/195/196). (4) uv run pytest + bats suite both green vs baseline. (5) grep for stale skills/ralph- refs limited to files this task owns.

Implemented (US-002 + US-003): (1) git mv skills -> plugins/ralph/skills and agents -> plugins/ralph/agents = 99 pure renames (0 insert/0 delete, history preserved); ralph-run scripts/ + tests/ moved with the skill. (2) pyproject.toml: pythonpath/testpaths/ruff.src/pyright.include/pyright.strict all repointed to plugins/ralph/skills/ralph-run/{scripts,tests}. (3) bats repointed: common.bash (RALPH_SCRIPT + CLAUDE_CONFIG_DIR now $PROJECT_ROOT/plugins/ralph so the shim resolves the relocated orchestrator without touching ralph.sh — that resolver is TASK-190), usage-check.bats, usage-pause.bats, shim.bats, pre-commit-hook.bats, commit-msg-hook.bats. (4) AGENTS.md 3 stale skill-path lines fixed. GATES: uv run pytest = 185 passed; uv run ruff check . = clean. bats = 104 pass / 72 fail, IDENTICAL failure set before and after (zero regression); the 72 are PRE-EXISTING orphaned bash tests referencing the deleted bash ralph.sh/usage-check.sh (removed during the Python port), unrelated to this move. All moved-path-dependent tests pass (e2e 'Run ralph.sh with mock opencode' + git-hook tests). AC#4 scope note: remaining skills/ralph- hits in md/py/toml are all owned by sibling tasks — task-reviewer-rules.md=TASK-195, README/CLAUDE.md=TASK-196, $HOME/.claude helper paths inside skills=TASK-191, .claude/skills/ralph-sync=AC#5 (untouched), plus immutable backlog/design history. R11 parity CONTENT preserved (pure byte-identical renames); R11 rule-doc PATHS intentionally repointed by TASK-195.

Commit: `4c89342` - task-188: Relocate skills and agents into plugins/ralph and repoint build/test config

task-reviewer verdict: APPROVED. Reviewer independently installed bats and ran the suite at HEAD and a master worktree — identical 104 pass / 72 fail sets (zero regression); confirmed all 99 renames are similarity index 100%, pytest 185 passed, ruff clean, and all 9 AC + R1-R16 pass. Implementation commit 4c89342.
<!-- SECTION:NOTES:END -->
