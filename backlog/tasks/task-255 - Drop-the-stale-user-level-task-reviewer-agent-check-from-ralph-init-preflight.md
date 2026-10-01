---
id: TASK-255
title: Drop the stale user-level task-reviewer agent check from ralph-init preflight
status: Done
assignee: []
created_date: '2026-10-01 05:23'
updated_date: '2026-10-01 05:59'
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
- [x] #1 grep -n '\.claude/agents/task-reviewer' plugins/ralph/skills/ralph-init/SKILL.md returns nothing
- [x] #2 ralph-init Step 1 states that the task-reviewer agent ships with the ralph plugin and is covered by the plugin-installed check
- [x] #3 Upgrade Mode U1, which runs Step 1's checks, no longer requires any user-level agent file
- [x] #4 A test in tests/python fails if ralph-init SKILL.md reintroduces a requirement on a file under .claude/agents, and asserts plugins/ralph/agents/task-reviewer.md exists
- [x] #5 Step 1's preflight snippets, run as written with HOME pointing at a directory that has a plugins/cache ralph install but no .claude/agents directory, exit 0; the command and its output are recorded in the task notes
- [x] #6 uv run ruff check . and uv run pytest pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: delete the user-level agent check + abort paragraph from ralph-init Step 1; add a sentence to the plugin-installed check that the plugin ships task-reviewer; add tests/python/test_init_no_user_agent_check.py that greps SKILL.md for .claude/agents requirements, asserts the plugin agent exists, and runs Step 1's bash snippets with a fake HOME.

AC5 run: HOME=$T/home (plugins/cache/dddpaul-ralph/ralph/0.8.2/skills/ralph-run/scripts/ralph_orchestrator.py present, no .claude/agents), CLAUDE_CONFIG_DIR unset, cwd a fresh git repo; each Step 1 ```bash block extracted from SKILL.md and run via bash -c "set -e\n<block>". Output: block 1 "exit 0 | .git / /usr/local/share/npm-global/bin/backlog"; block 2 "exit 0" (no output); agents dir exists: False. Same run is pinned by tests/python/test_init_preflight_no_user_agent.py (fails 2/3 against the old SKILL.md). U1 delegates to Step 1, so it no longer needs a user-level agent. ruff clean; pytest 678 passed.

Commit: `99041a6` - task-255: drop the user-level task-reviewer check from ralph-init preflight

Done: task-reviewer APPROVED. Test file is tests/python/test_init_preflight_no_user_agent.py (the plan note named it differently). Guard scans bash blocks only, because the new prose itself has to mention ~/.claude/agents/; the run-as-written test catches any executable check. Final gates: ruff clean, pytest 678 passed.

Commit: `d18a3b5` - task-255: bump plugin version to 0.8.3 (patch)
<!-- SECTION:NOTES:END -->
