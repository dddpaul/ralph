---
id: TASK-255
title: Drop the stale user-level task-reviewer agent check from ralph-init preflight
status: To Do
assignee: []
created_date: '2026-10-01 05:23'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

ralph-init Step 1 in `plugins/ralph/skills/ralph-init/SKILL.md` (the block at roughly lines 44-51) aborts unless a user-level agent file exists:

```bash
[ -s "$HOME/.claude/agents/task-reviewer.md" ] || {
  echo "ERROR: ~/.claude/agents/task-reviewer.md missing. Copy it from the Ralph repo:"
  echo "  cp <ralph-repo>/agents/task-reviewer.md ~/.claude/agents/"
  exit 1
}
```

followed by the paragraph "If the user-global agent file is missing, print the error and **abort** — do NOT proceed to Step 2 or write any project files."

The check dates from TASK-92, when the agent lived at the user level. Since the marketplace migration the agent ships inside the ralph plugin (`plugins/ralph/agents/task-reviewer.md`, present in the installed plugin cache) and resolves as `ralph:task-reviewer`. Nothing creates the user-level file any more, and the suggested `cp` source path no longer exists.

Observed 2026-10-01: `/ralph:ralph-init` on a machine with no user-level agents directory stopped at preflight and wrote no project files.

**Upgrade Mode is hit too.** U1 says "Run the same checks as Step 1", so `ralph upgrade` aborts the same way. This blocks the planned fleet upgrade sweep.

## Fix

Delete the stale check block and its abort paragraph. The very next Step 1 check already covers the agent — it verifies the ralph plugin is installed by finding `ralph_orchestrator.py` in the plugin cache, and the agent ships in that same plugin. Add one sentence to that check's explanation saying the plugin also ships the task-reviewer agent, so no user-level copy is needed.

The mentions of a user-level agents directory in `.claude/task-reviewer-rules.md` are generic lists of places an agent file may live; they require nothing and need no change.

## Out of scope

- Changing where the agent ships.
- The reviewer rules file.
- Any other preflight check.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 grep -n '\.claude/agents/task-reviewer' plugins/ralph/skills/ralph-init/SKILL.md returns nothing
- [ ] #2 ralph-init Step 1 states that the task-reviewer agent ships with the ralph plugin and is covered by the plugin-installed check
- [ ] #3 Upgrade Mode U1, which runs Step 1's checks, no longer requires any user-level agent file
- [ ] #4 A test in tests/python fails if ralph-init SKILL.md reintroduces a requirement on a file under .claude/agents, and asserts plugins/ralph/agents/task-reviewer.md exists
- [ ] #5 Step 1's preflight snippets, run as written with HOME pointing at a directory that has a plugins/cache ralph install but no .claude/agents directory, exit 0; the command and its output are recorded in the task notes
- [ ] #6 uv run ruff check . and uv run pytest pass
<!-- AC:END -->
