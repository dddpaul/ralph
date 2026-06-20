---
id: TASK-142
title: 'Fix task-validator check 7: gate on SUBSTANTIVE and tighten path heuristic'
status: Done
assignee: []
created_date: '2026-06-20 18:05'
updated_date: '2026-06-20 18:51'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The PostToolUse task-validator hook (.claude/hooks/task-validator.sh) emits "Referenced path 'X' does not exist" complaints from check #7. Across three Ralph-bootstrapped projects, session logs show 364 + 64 + 63 = 491 firings with ~80-90% false positives. Two compounding bugs.

**Bug 1 (main, ~90% of noise): check #7 runs unconditionally.**
Lines 98-132 scan every backtick span and markdown link for path existence on every Bash invocation. Across 364 -workspace fires, ZERO followed a `-d` description rewrite — the same stale path warnings re-emit on every `-s` status change, `--check-ac` flip, `--append-notes`, even unrelated `ls`. A single bad reference fires 50 times across the task lifecycle.

Fix: move check #7 inside the SUBSTANTIVE gate the LLM rubric already uses (lines 165-227). Compute SUBSTANTIVE once at the top, then gate both check #7 and the rubric on it. Status-only and AC-checkbox-only edits skip check #7 entirely.

**Bug 2 (residual, when description IS edited): heuristic too loose.**
Current accept rule at line 124: must contain `/` OR end with `.sh|.js|.ts|.py|.md|.json|.yaml|.yml|.toml`. Too broad — `.js` alone, `<br/>`, `/ralph-init`, `$path`, `node foo.js`, `<a:effectLst/>` all pass and get flagged as "missing paths". Add skip rules BEFORE existence check:

- whitespace in the string (command-line snippets: `node foo.js`, `rm -rf /`)
- starts with `<` and ends with `>` (HTML/XML tag literals)
- contains `$` (shell var expansions: `$path`, `$TARGET_DIR/X`)
- contains embedded `<...>` placeholder syntax (`path/to/<name>`, `attachments-<id>/`)
- starts with `/` followed by single lowercase word (slash-commands, URL fragments: `/ralph-init`, `/rest/plantuml/`)
- bare extension only (`.js`, `.py`, `.md` with no name)

Preserve existing skips: URLs (`^https?://|^www\.`), wildcards (`[*?]|\.\.\.`).

**R11 mirror.** Both files updated identically:
- `.claude/hooks/task-validator.sh` (live)
- `skills/ralph-init/templates/claude/hooks/task-validator.sh` (template)

**Smoke test.** Create a synthetic task body containing one real path (e.g. `.claude/hooks/task-validator.sh`) and one fake path in a backtick span; verify the validator:
- DOES fire when `backlog task edit N -d` rewrites the description with the fake path
- DOES NOT fire when `backlog task edit N -s "In Progress"` (status-only) is run against the same body
- DOES NOT fire on tag literals, `$vars`, slash-commands, bare extensions when description IS edited

Evidence corpus:
```
~/.claude/projects/-Users-paul-workspace/*.jsonl                  → 364 fires
~/.claude/projects/-Users-paul-Private-Alfa-Projects-equation-core/*.jsonl → 64 fires
~/.claude/projects/-Users-paul-Private-Projects-claude-skills/*.jsonl     → 63 fires
```
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Check #7 (path-existence scan, lines 98-132 in current file) runs only when SUBSTANTIVE=true
- [x] #2 SUBSTANTIVE computation is hoisted/reused — not duplicated between the new gate and the existing LLM rubric gate
- [x] #3 Heuristic skips added: whitespace, HTML/XML tag literals (<...>), shell vars ($X), embedded <placeholder> syntax, slash-command/URL-fragment /word, bare extensions
- [x] #4 Existing skips preserved: URLs (^https?://|^www\\.), wildcards ([*?]|\\.\\.\\.), require-/-or-known-extension acceptance rule
- [x] #5 skills/ralph-init/templates/claude/hooks/task-validator.sh updated identically to .claude/hooks/task-validator.sh (diff produces no output)
- [x] #6 Smoke test passes: validator fires on fake path during -d rewrite, silent on -s status-only edit, silent on tag/var/slash-command/bare-extension noise
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: 1) Hoist SUBSTANTIVE computation above check #7. 2) Gate check #7 on SUBSTANTIVE=true. 3) Add new skip rules in check #7's path filter: whitespace, <tag>/<...placeholder>, $vars, slash-commands /word, bare extensions. 4) Mirror to skills/ralph-init/templates/. 5) Smoke test via simulated stdin invocations of the hook.

task-reviewer APPROVED. All 6 AC pass; smoke test green (16/16 + 5 independently re-run scenarios). R11 mirror byte-identical.

Commit: `f4fdcd7` - task-142: Gate validator check #7 on SUBSTANTIVE; tighten path heuristic
<!-- SECTION:NOTES:END -->
