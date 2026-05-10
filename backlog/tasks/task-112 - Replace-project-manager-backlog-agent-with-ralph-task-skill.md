---
id: TASK-112
title: Replace project-manager-backlog agent with ralph-task skill
status: Done
assignee: []
created_date: '2026-05-09 17:03'
updated_date: '2026-05-10 11:29'
labels:
  - 'feature:ralph-task'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Drop the buggy user-global project-manager-backlog agent and replace its narrow Ralph-project role with a thin project-level ralph-task skill. The agent has three deep defects (witnessed in TASK-110/111 creation):

1. 4 examples instruct comma-joined --ac "a,b,c"; the CLI does NOT split on commas, so all criteria collapse into one AC.
2. "Code snippets should be avoided" in description guidance conflicts with autonomous Ralph execution (TASK-110 lost its pre-designed grep pipeline).
3. No post-create self-verification step; the agent self-reported "6 ACs created" while only producing 1 collapsed AC.

Replacement is a thin skill (~60-80 lines) with three MUST rules + a 6-rule decomposition heuristic + mandatory self-check.

Full design is in design/ralph-task-brainstorm.md. Key load-bearing details:

## Canonical pattern the skill must document

```bash
backlog task create "<English title>" \
  -d "<WHY: paragraph + code blocks for verbatim implementer use>" \
  --ac "<atomic outcome 1>" \
  --ac "<atomic outcome 2>" \
  --priority <high|medium|low>
```

MUST: repeat --ac per criterion (CLI does not split on commas).
MUST: description may carry code blocks (regex, bash, SQL) for autonomous Ralph.
MUST: -l "feature:<name>" optional. If user names a feature, verify design/<name>-prd.md or design/<name>-brainstorm.md exists; warn if not.

## 6-rule decomposition heuristic (skill content)

| # | Rule | Signal |
|---|---|---|
| 0 | Purpose-value (highest) | One task = one user-visible deliverable; intermediates are ACs |
| 1 | One-PR | ~10 ACs soft cap |
| 2 | Dependency | Cross-purpose-value reference -> split + --dep |
| 3 | Mirror (R11) | Mechanical mirror -> same task |
| 4 | Rollback | Partial merge breaks coherence -> same task |
| 5 | Verification | Every AC objectively pass/fail |

Cadence note: autonomous Ralph favors 5-7 ACs; human-led runs closer to 10.

## Mandatory self-check after create

```bash
backlog task view <id> --plain | grep -A20 "Acceptance"
```

If a single AC line has commas joining what should be separate items, fix with:

```bash
backlog task edit <id> --remove-ac N --ac "..." --ac "..."
```

## Wiring

- .claude/brainstorm-rules.md Phase 4 first option names ralph-task explicitly
- CLAUDE.md Task Lifecycle gets 2-line pointer (ralph-task ad-hoc; ralph-prd->ralph-backlog for PRDs)
- README.md unchanged
- ~/.claude/agents/project-manager-backlog.md deleted
- ralph-sync auto-picks up new skill folder

See design/ralph-task-brainstorm.md for full hand-off, scope cuts, and open questions.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-task/SKILL.md documents the canonical 'backlog task create' pattern with three MUST rules: repeated --ac flags, code blocks allowed in -d, feature:<slug> label optional with design-doc sanity check
- [x] #2 skills/ralph-task/SKILL.md documents the 6-rule decomposition heuristic exactly as in design/ralph-task-brainstorm.md: 0 Purpose-value, 1 One-PR (~10 ACs cap), 2 Dependency, 3 Mirror (R11), 4 Rollback, 5 Verification — plus the cadence note (autonomous 5-7, human ~10)
- [x] #3 skills/ralph-task/SKILL.md documents the mandatory self-check: 'backlog task view <id> --plain | grep -A20 Acceptance' and the fix recipe 'backlog task edit <id> --remove-ac N --ac ... --ac ...'
- [x] #4 .claude/brainstorm-rules.md Phase 4 first option text is updated to explicitly name the ralph-task skill (replacing the implicit project-manager-backlog grab)
- [x] #5 CLAUDE.md Task Lifecycle section contains a 1-2 line pointer: ralph-task for ad-hoc, ralph-prd then ralph-backlog for PRD-driven feature work
- [x] #6 ~/.claude/agents/project-manager-backlog.md is deleted (verifiable: 'ls ~/.claude/agents/project-manager-backlog.md' returns 'No such file')
- [x] #7 After merge, 'bash .claude/skills/ralph-sync/sync.sh classify' shows skills/ralph-task/SKILL.md as [new] before sync, [unchanged] after
- [x] #8 skills/ralph-task/SKILL.md documents the path-fence writing rule: paths to created-on-merge files (including the SKILL.md's own forward references) appear inside fenced code blocks to avoid task-validator hook false-positive flags from its path-existence check
- [x] #9 skills/ralph-task/SKILL.md exists with valid YAML frontmatter (name: ralph-task, description triggers on semantic intent in any natural language — English examples: create a task / add a task / new task / track this as a task; Russian examples: создай задачу / добавь задачу / новая задача / оформи задачу — and the description text states matching is by intent, not exact keyword)
- [x] #10 skills/ralph-task/SKILL.md 'Editing existing tasks' section exists with language-agnostic conversational deliberation triggers (English: split this task / scope grew / AC unclear / belongs to TASK-X; Russian: разбить задачу / расширилась задача / AC размытый / переложить в отдельную задачу), applies the 6 rules with decision recipes (split into sibling task with --dep vs add as new AC), and redirects mechanical ops (--check-ac, status, --append-notes, --add-label, --priority, -t) to CLAUDE.md
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) Create skills/ralph-task/SKILL.md following design/ralph-task-brainstorm.md — three MUST rules, 6-rule decomposition heuristic table, mandatory self-check, editing-existing-tasks section with conversational triggers, language-agnostic creation+edit triggers (English+Russian), path-fence writing rule. (2) Update .claude/brainstorm-rules.md Phase 4 first option to name ralph-task. (3) Add Task Lifecycle pointer (~2 lines) to CLAUDE.md and remove the stale project-manager-backlog reference. (4) Delete ~/.claude/agents/project-manager-backlog.md. (5) Verify ralph-sync classify shows skills/ralph-task/SKILL.md as [new]. (6) Run task-reviewer agent on diff. (7) Final lint via bash -n on sync.sh + classify run; merge.

Commit: `96ce97a` - task-112: Replace project-manager-backlog agent with ralph-task skill

Implemented ralph-task skill at skills/ralph-task/SKILL.md (214 lines) with three MUST rules, the 6-rule decomposition heuristic + cadence note, mandatory self-check, English+Russian intent-based triggers, editing-existing-tasks section with decision recipes A/B/C, mechanical-ops redirect to CLAUDE.md, and the path-fence writing rule. Updated .claude/brainstorm-rules.md Phase 4 first option to invoke ralph-task; updated CLAUDE.md Task Lifecycle to point to ralph-task (ad-hoc + edit deliberation) and ralph-prd -> ralph-backlog (PRD-driven). Deleted user-global ~/.claude/agents/project-manager-backlog.md. Removed stale project-manager-backlog reference from skills/ralph-init/templates/root/CLAUDE.md to prevent footgun for new bootstraps. ralph-sync round-trip verified: pre-sync [new], post-sync [unchanged]. task-reviewer agent: APPROVED.
<!-- SECTION:NOTES:END -->
