---
id: TASK-82
title: Add task-validator PostToolUse hook (deterministic + in-session LLM advisory)
status: To Do
assignee: []
created_date: '2026-05-01 16:56'
updated_date: '2026-05-01 17:02'
labels:
  - hook
  - validator
  - task-management
  - interactive
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a PostToolUse hook that validates a backlog task after every edit, surfacing issues to the user in interactive mode before Ralph picks the task up. Validation runs in two phases: cheap deterministic structural checks (synchronous, blocking, warn-only output) and an in-session LLM advisory check (asynchronous nudge to the current Claude session via system-reminder).

Background and rationale:

- Task crafting is iterative; partial edits often leave the rest of the task contradicting the new piece. By the time Ralph picks the task up in autonomous mode it is too late — Ralph would implement a confused task or fail mid-iteration.
- Validation must happen during interactive task crafting, not during Ralph's autonomous loop.
- The validator must NOT bloat Ralph's autonomous prompt or interrupt its single-task focus.

Design summary:

1. Trigger: PostToolUse hook on Bash tool calls matching 'backlog task edit *' and 'backlog task create *'.

2. Hook short-circuit if RALPH_AUTONOMOUS=1 is exported. ralph.sh must export this before the 'claude --dangerously-skip-permissions --print' invocation so hooks fired inside the autonomous claude process can detect autonomous mode and skip the LLM nudge AND suppress the deterministic-check output (deterministic checks may still run, but their output is suppressed in autonomous mode to avoid distracting Ralph).

3. Deterministic checks (synchronous, warn-only on stdout):
   1. Description body is non-empty after stripping frontmatter and the title heading.
   2. At least one acceptance criterion present.
   3. No empty AC line ('- [ ]' or '- [x]' with no content after the checkbox).
   4. No identical AC strings after normalization (lowercase, trim, collapse whitespace).
   5. status: Done is consistent with all AC checked (and vice versa: all AC checked but status \!= Done is a warn).
   6. Listed dependencies (frontmatter 'dependencies' field) resolve to existing task IDs in backlog/tasks/.
   7. File-path references that look meant-as-real exist in the repo. To avoid false positives on illustrative examples in prose, only check paths that appear in one of these contexts:
      - Inside backtick-quoted spans: `path`
      - Inside markdown link syntax: [label](path)
      - As YAML frontmatter values
      Skip:
      - Paths inside fenced code blocks (``` ... ```).
      - Bareword paths in prose without backticks/link syntax (treated as illustrative).
      - Wildcard or glob patterns containing '*', '?', or '...'.
      Only runs on substantive edits.
   Each failed check prints one line: 'Validator [det]: <issue>'. Non-blocking — the edit always succeeds. Suppressed entirely when RALPH_AUTONOMOUS=1.

4. Substantive-edit predicate: 'git diff HEAD -- backlog/tasks/task-N*' shows changes in the description body or in any AC line. If the diff is empty, or only touches Notes / frontmatter (other than dependencies, status, AC structure) / AC checkboxes, the LLM nudge is skipped.

5. LLM nudge: when substantive AND not autonomous, the hook prints to stdout a <system-reminder> block containing:
   - Task ID and the path to the task file (no body dump — Claude reads it fresh).
   - Rubric items: (1) logical contradictions, (2) semantic AC duplication, (3) AC implementability, (4) reference reachability — only included if the task body contains URLs (regex 'https?://|www\\.'); when included, the reminder points at .devcontainer/init-firewall.sh by path rather than inlining the host list, (5) self-containment.
   - Output format spec: 'Validator [llm]: task-N OK' or 'Validator [llm]: task-N' followed by terse one-line issues. No remediation, no rewrites.
   - Numbering renumbered 1..N when reachability is omitted.

6. Findings landing: system-reminder only — Claude announces findings inline at the top of its next reply. No --append-notes, no sidecar file, no automated gating, no label flipping. Validator output is for the user's interactive crafting flow; Ralph never sees it (RALPH_AUTONOMOUS suppresses).

7. ralph.sh change: export RALPH_AUTONOMOUS=1 in the iteration loop's environment, scoped so the variable is set when the per-iteration 'timeout … claude --print …' command runs and unset (or absent) outside that command. Locate the insertion point by the 'timeout … claude' invocation, NOT by hard-coded line number. Verified safe: no existing hook reads this name and no CLAUDE.md autonomous-mode logic depends on it (CLAUDE.md autonomous trigger is prompt-text-based 'MODE: autonomous').

8. Hook script implementation:
   - Single bash script at `.claude/hooks/task-validator.sh` referenced from `.claude/settings.json` under hooks.PostToolUse.
   - Uses jq to parse tool_input.command, sed/grep to extract task ID, awk/sed to parse the markdown sections.
   - Cheap and self-contained; runs without network access.

9. Template propagation: also add the hook script and settings.json entry to skills/ralph-init/templates/ so future projects inherit the validator on init/upgrade.

Out of scope for v1:
- Atomicity / scope-creep checks (task spans multiple unrelated changes).
- AC-vs-description coverage check (subjective, hard to make terse).
- Auto-gating (label-flipping to block Ralph pickup until validator clears).
- Banner/sound/push-notification alerting.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 PostToolUse hook entry added to .claude/settings.json matching Bash tool calls with command pattern 'backlog task edit *' or 'backlog task create *'
- [ ] #2 Hook script .claude/hooks/task-validator.sh implements all 7 deterministic checks described in the task body
- [ ] #3 Hook short-circuits the LLM nudge when RALPH_AUTONOMOUS=1 is set in the environment
- [ ] #4 Substantive-edit predicate uses 'git diff HEAD -- backlog/tasks/task-N*' and only fires the LLM nudge when description body or AC text changed
- [ ] #5 LLM nudge is emitted as a <system-reminder> block on stdout containing only the task ID and file path, not the task body
- [ ] #6 Rubric item 4 (reference reachability) is included in the system-reminder ONLY when the task body matches the URL regex 'https?://|www\.'; when omitted, remaining rubric items are renumbered 1..N
- [ ] #7 When item 4 is included, it points at .devcontainer/init-firewall.sh by path; the file's content is NOT inlined
- [ ] #8 Output format for the LLM matches the spec: 'Validator [llm]: task-N OK' or 'Validator [llm]: task-N' followed by terse one-line issues, no remediation
- [ ] #9 Deterministic check failures print 'Validator [det]: <issue>' lines on stdout (suppressed when RALPH_AUTONOMOUS=1) and never block the edit
- [ ] #10 ralph.sh exports RALPH_AUTONOMOUS=1 in the iteration loop's environment, scoped so the variable is set when the per-iteration 'timeout … claude --print …' command runs and unset outside that command (no hard-coded line number; locate by the timeout/claude invocation)
- [ ] #11 skills/ralph-init/templates/ contains both the hook script and the settings.json hook entry so that future projects ship the validator
- [ ] #12 Manual smoke test: edit a task to introduce a logical contradiction (e.g. AC1 says use TypeScript, AC2 says use Go); next interactive Claude reply contains a 'Validator [llm]: task-N' block flagging the contradiction
- [ ] #13 Manual smoke test: edit a task with --append-notes or --check-ac; no LLM nudge fires (substantive predicate skips), only deterministic checks run if applicable
- [ ] #14 Manual smoke test: simulate Ralph by exporting RALPH_AUTONOMOUS=1 and running 'backlog task edit' that would otherwise fire the nudge; verify the system-reminder is suppressed and the deterministic-check stdout is suppressed too (consistent with AC #9)
- [ ] #15 Manual smoke test: edit a task whose body contains no URLs; system-reminder rubric does not include the reachability item, and item numbering is contiguous
- [ ] #16 Manual smoke test: edit a task whose body contains a URL; system-reminder includes reachability item pointing at .devcontainer/init-firewall.sh by path, no host list inlined
<!-- AC:END -->
