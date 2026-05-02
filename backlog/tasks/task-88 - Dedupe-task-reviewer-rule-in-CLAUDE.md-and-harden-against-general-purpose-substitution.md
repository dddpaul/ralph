---
id: TASK-88
title: >-
  Dedupe task-reviewer rule in CLAUDE.md and harden against general-purpose
  substitution
status: Done
assignee: []
created_date: '2026-05-02 15:28'
updated_date: '2026-05-02 16:15'
labels:
  - docs
  - workflow
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
CLAUDE.md states the same task-reviewer rule twice: in lifecycle step 4 (line 27) and in the ### Code Review section under ## Rules (lines 60-61). The Code Review section adds 'Only merge after approval' but otherwise duplicates the lifecycle step.

Recent incident: I (Claude in this session) reviewed TASK-86/87 changes using the general-purpose agent instead of task-reviewer, producing a false-positive AC #5 violation (the orphan task-file-guard.sh case) that nearly caused a needless task-87 reopen. The dedicated task-reviewer agent is anchored on git diff master..HEAD per its definition, which would have evaluated AC #5 correctly.

Hook-based enforcement is not feasible: PreToolUse/PostToolUse hooks do not fire for the Task tool that spawns subagents (Claude Code issues #20243, #34692). The realistic mitigation is documentation: dedupe the rule and harden the wording so substitution with general-purpose is explicitly forbidden.

## Resolution

1. Replace lifecycle step 4 with a strengthened single-source statement that includes the merge gate and forbids substitution.
2. Delete the redundant ### Code Review section.
3. Apply the same change to skills/ralph-init/templates/CLAUDE.md.

Proposed step 4 wording:

  4. **Review:** after tests pass, spawn the `task-reviewer` agent (NOT `general-purpose` or any other) on `git diff master..HEAD`. Do not proceed to step 5 (Done) or step 6 (Merge) without an APPROVED verdict from the task-reviewer agent.

## Out of scope

- Hook-based enforcement of task-reviewer invocation (blocked by Claude Code subagent hook bypass — would require SubagentStop hook probe, deferred).
- Renaming or restructuring other CLAUDE.md sections.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Lifecycle step 4 in CLAUDE.md is rewritten to include the merge gate (do not proceed to Done/Merge without APPROVED) and explicitly forbids substituting the task-reviewer agent with general-purpose or any other
- [x] #2 The ### Code Review section under ## Rules is deleted in CLAUDE.md (the rule now lives only in lifecycle step 4)
- [x] #3 skills/ralph-init/templates/CLAUDE.md receives the same edits in the same locations
- [x] #4 Manual smoke check: grep -n task-reviewer CLAUDE.md returns exactly one location (lifecycle step 4 region) in both project and template CLAUDE.md
- [x] #5 task-reviewer.md has YAML frontmatter (name: task-reviewer, description, color) so subagent_type=task-reviewer is registered as a valid Agent tool enum value in new Claude Code sessions
- [x] #6 Same frontmatter applied to skills/ralph-init/templates/task-reviewer.md and ~/.claude/agents/task-reviewer.md (user-global mirror)
- [x] #7 Smoke check: head -5 of all three task-reviewer.md files shows the same frontmatter block
- [x] #8 DEFERRED to next session: invoke subagent_type=task-reviewer on this task's diff and confirm APPROVED verdict; only then mark task Done and merge to master
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: 1) Rewrite lifecycle step 4 in CLAUDE.md (line 27). 2) Delete ### Code Review section (lines 60-61). 3) Mirror to skills/ralph-init/templates/CLAUDE.md. 4) Run task-reviewer. 5) Mark Done and merge.

Commit: `da18437` - task-88: Dedupe task-reviewer rule in CLAUDE.md and template

Discovery: task-reviewer.md previously had no frontmatter, so subagent_type=task-reviewer was not registered in Claude Code's Agent tool enum. The CLAUDE.md rule was unenforceable at the tool layer until this fix. Added frontmatter to project, template, and user-global. AC #5 (verify by invoking subagent_type=task-reviewer) is deferred to a fresh Claude Code session because the Agent tool's subagent_type enum is fixed at session start.

Commit: `0ad7ad7` - task-88: Add YAML frontmatter to task-reviewer agent for subagent_type registration

AC #8: Spawned subagent_type=task-reviewer in fresh session on git diff master..HEAD. Verdict: APPROVED. All 8 ACs and the 8-item review checklist pass. Frontmatter registration confirmed working — task-reviewer is now in the Agent tool enum at session start.
<!-- SECTION:NOTES:END -->
