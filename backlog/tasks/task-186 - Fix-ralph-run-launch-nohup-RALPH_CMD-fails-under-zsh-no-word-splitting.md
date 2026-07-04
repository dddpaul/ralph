---
id: TASK-186
title: 'Fix ralph-run launch: nohup $RALPH_CMD fails under zsh (no word splitting)'
status: To Do
assignee: []
created_date: '2026-07-03 05:07'
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
- [ ] #1 ralph-run SKILL.md Step 4 no longer depends on unquoted $RALPH_CMD word-splitting; the launch behaves identically under bash and zsh
- [ ] #2 The launch passes ./ralph.sh as argv[0] and each flag as a separate argument (verified: orchestrator starts and a fresh heartbeat appears, wait-heartbeat.sh returns OK) under zsh
- [ ] #3 A short inline note documents the zsh word-splitting pitfall so the string-variable form is not reintroduced
<!-- AC:END -->
