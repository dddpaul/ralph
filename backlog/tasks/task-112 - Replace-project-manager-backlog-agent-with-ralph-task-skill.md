---
id: TASK-112
title: Replace project-manager-backlog agent with ralph-task skill
status: To Do
assignee: []
created_date: '2026-05-09 17:03'
updated_date: '2026-05-09 18:34'
labels: []
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
- [ ] #1 skills/ralph-task/SKILL.md exists with valid YAML frontmatter (name: ralph-task, description with triggers: create a task / add a task / new task / track this as a task)
- [ ] #2 skills/ralph-task/SKILL.md documents the canonical 'backlog task create' pattern with three MUST rules: repeated --ac flags, code blocks allowed in -d, feature:<slug> label optional with design-doc sanity check
- [ ] #3 skills/ralph-task/SKILL.md documents the 6-rule decomposition heuristic exactly as in design/ralph-task-brainstorm.md: 0 Purpose-value, 1 One-PR (~10 ACs cap), 2 Dependency, 3 Mirror (R11), 4 Rollback, 5 Verification — plus the cadence note (autonomous 5-7, human ~10)
- [ ] #4 skills/ralph-task/SKILL.md documents the mandatory self-check: 'backlog task view <id> --plain | grep -A20 Acceptance' and the fix recipe 'backlog task edit <id> --remove-ac N --ac ... --ac ...'
- [ ] #5 .claude/brainstorm-rules.md Phase 4 first option text is updated to explicitly name the ralph-task skill (replacing the implicit project-manager-backlog grab)
- [ ] #6 CLAUDE.md Task Lifecycle section contains a 1-2 line pointer: ralph-task for ad-hoc, ralph-prd then ralph-backlog for PRD-driven feature work
- [ ] #7 ~/.claude/agents/project-manager-backlog.md is deleted (verifiable: 'ls ~/.claude/agents/project-manager-backlog.md' returns 'No such file')
- [ ] #8 After merge, 'bash .claude/skills/ralph-sync/sync.sh classify' shows skills/ralph-task/SKILL.md as [new] before sync, [unchanged] after
- [ ] #9 skills/ralph-task/SKILL.md 'Editing existing tasks' section exists with conversational deliberation triggers (split this task / scope grew / AC unclear / belongs to TASK-X), applies the 6 rules with decision recipes (split into sibling task with --dep vs add as new AC), and explicitly redirects mechanical ops (--check-ac, status, --append-notes, --dep, --add-label, --priority, -t) to CLAUDE.md
- [ ] #10 skills/ralph-task/SKILL.md documents the path-fence writing rule: paths to created-on-merge files (including the SKILL.md's own forward references) appear inside fenced code blocks to avoid task-validator hook false-positive flags from its path-existence check
<!-- AC:END -->
