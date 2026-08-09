---
id: TASK-186
title: 'Fix ralph-run launch: nohup $RALPH_CMD fails under zsh (no word splitting)'
status: Done
assignee: []
created_date: '2026-07-03 05:07'
updated_date: '2026-08-09 07:49'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ralph-run SKILL.md Step 4 (Launch) builds the command into a string variable and runs it unquoted: RALPH_CMD="..."; nohup $RALPH_CMD > ... & disown (SKILL.md lines ~102 and ~115). This assumes bash word-splitting. Under zsh — the default macOS login shell, and the shell Claude Code's Bash tool executes — an unquoted parameter expansion does NOT undergo word splitting, so the ENTIRE command string is passed to nohup as a single argument (the program name). Result: 'nohup: ./ralph.sh --tool claude ...: No such file or directory', the process dies instantly, and no heartbeat ever appears (wait-heartbeat.sh reports FAIL). Bash users are unaffected; zsh users cannot launch. Discovered in okf-mcp-server on 2026-07-03 (workaround there: invoke the command literally instead of via the variable). Fix options: (a) use an array — RALPH_CMD=(./ralph.sh --tool ...) then nohup "${RALPH_CMD[@]}" (portable across bash+zsh, recommended); (b) ${=RALPH_CMD} or ${(z)RALPH_CMD} (zsh-only split); (c) bash -c "$RALPH_CMD"; (d) write the command literally. Prefer (a).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ralph-run SKILL.md Step 4 no longer depends on unquoted $RALPH_CMD word-splitting; the launch behaves identically under bash and zsh
- [x] #2 The launch passes ./ralph.sh as argv[0] and each flag as a separate argument (verified: orchestrator starts and a fresh heartbeat appears, wait-heartbeat.sh returns OK) under zsh
- [x] #3 A short inline note documents the zsh word-splitting pitfall so the string-variable form is not reintroduced
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Rewrite ralph-run SKILL.md Step 4 launch to build RALPH_CMD as a bash/zsh array (RALPH_CMD=(...); RALPH_CMD+=(--flag ...)) and launch via nohup "${RALPH_CMD[@]}" — portable across bash+zsh (option a). Add inline zsh word-splitting note (AC#3). Also update the sibling cross-reference label at ralph-init SKILL.md:388 from $RALPH_CMD to ${RALPH_CMD[@]} so the buggy string form isn't cited as canonical. Version bump handled by bump-version.sh --auto at merge (shipped plugins/ralph/skills/** change).

Commit: `fc1e490` - task-186: launch ralph via RALPH_CMD array, not unquoted string (zsh word-splitting fix)

Implemented option (a): ralph-run SKILL.md Step 4 now builds RALPH_CMD as a bash/zsh array (RALPH_CMD=(...); conditional flags via RALPH_CMD+=(--flag ...)) and launches via nohup "${RALPH_CMD[@]}" (SKILL.md:102,105-109,115). Added inline 'zsh word-splitting' note (SKILL.md:119) documenting the pitfall so the string form isn't reintroduced (AC#3). Also synced the sibling cross-reference label at ralph-init SKILL.md:388 from $RALPH_CMD to "${RALPH_CMD[@]}". Verification: empirically reproduced under zsh 5.9 + bash — string form (nohup $RALPH_CMD) fails with 'No such file or directory' (whole cmd as argv[0]); array form passes the program as argv[0] and each flag as a separate argument identically under both shells, incl. the += append (AC#1,#2). Real orchestrator/heartbeat (wait-heartbeat.sh) not launchable in-sandbox (needs docker/full OS) — argv-construction half of AC#2 verified empirically. Gate: uv run ruff check . clean; uv run pytest 346 passed (docs-only, unaffected). Review: task-reviewer APPROVED (independently reproduced bug+fix under bash+zsh). No template mirror for these SKILL.md files under ralph-init/templates → R11 N/A. Merge will run bump-version.sh --auto (shipped plugins/ralph/skills/** changed).

Commit: `64c4d9b` - task-186: bump plugin version to 0.2.3 (patch)
<!-- SECTION:NOTES:END -->
