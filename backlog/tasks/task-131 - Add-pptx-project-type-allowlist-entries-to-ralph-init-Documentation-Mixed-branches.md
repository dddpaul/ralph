---
id: TASK-131
title: >-
  Add pptx project-type allowlist entries to ralph-init (Documentation/Mixed
  branches)
status: Done
assignee: []
created_date: '2026-05-19 08:45'
updated_date: '2026-05-19 13:33'
labels: []
dependencies:
  - TASK-127
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Split from TASK-127 (Section E). When ralph-init's project-type question (Q1) is answered `Documentation` or `Mixed`, the init flow already provisions Obsidian config and devcontainer support for pptx work. But the `example-skills:pptx` skill body shells out to:

- `python scripts/office/soffice.py` (LibreOffice headless conversion)
- `pdftoppm` (PDF → image rasterization)

Neither is in the template allowlist. Result: in a Documentation project, pptx skill workflows trip permission prompts on every conversion.

Narrower impact than sibling tasks 128 / 129 / 130 — only affects Documentation / Mixed project types — hence medium priority.

## Scope

`skills/ralph-init/SKILL.md` Step 3.7b (or a new sub-step gated on `project_type ∈ {Documentation, Mixed}`): emit two narrow-form rules into `settings.local.json`:

```
Bash(python scripts/office/soffice.py:*)
Bash(pdftoppm:*)
```

## Out of scope

- `Bash(python:*)` blanket allow — too broad; keep the path-narrowed form.
- Adding `soffice` / `pdftoppm` to the devcontainer Dockerfile — assumed already in place from the Documentation project-type setup; if not, surface as a follow-up.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 When project_type is Documentation or Mixed, ralph-init Step 3.7b (or equivalent gated sub-step) writes Bash(python scripts/office/soffice.py:*) and Bash(pdftoppm:*) to .claude/settings.local.json
- [x] #2 When project_type is Code-only, neither pptx rule is added (verified by fixture init with Code project type)
- [x] #3 Step 3.10 verification, when project_type is Documentation/Mixed, also checks both pptx rules and surfaces a WARN naming the missing one
- [ ] #4 Smoke test: in a fresh Documentation project, invoking example-skills:pptx workflow does not trigger a permission prompt for the python soffice or pdftoppm commands
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Add new gated Step 3.7c to skills/ralph-init/SKILL.md (after 3.7b) that runs only when project_type ∈ {Documentation, Mixed}; emits Bash(python scripts/office/soffice.py:*) and Bash(pdftoppm:*) into .claude/settings.local.json via idempotent jq merge (same pattern as 3.7b). Code-only projects print a [skip] line (satisfies AC#2 — rules never added). Extend Step 3.10 with a project-type-gated pptx-rule verification block that WARNs naming each missing rule (AC#3). Validate jq snippets with bash -n + a fixture merge against the real template settings.local.json proving both rules land and Code-only path leaves them absent. AC#4 (live pptx permission-prompt smoke test) deferred for manual verification per sibling task-128/129 precedent — not automatable in autonomous loop.

Commit: `bf7520d` - task-131: Add gated pptx helper allowlist sub-step to ralph-init

Implemented Step 3.7c (gated on project_type ∈ {Documentation,Mixed}) merging Bash(python scripts/office/soffice.py:*) and Bash(pdftoppm:*) into .claude/settings.local.json via idempotent jq; Code-only prints [skip] and never adds them (AC#1/#2). Step 3.10 extended with a project-type-gated pptx verification block that WARNs naming each missing rule (AC#3, fixture-verified PASS/WARN/partial). U4 upgrade flow re-applies 3.7c for Documentation/Mixed (detected via .obsidian/) so template overwrite does not strip the rules. Validation: bash -n on full Step 3.10 block OK; fixture merge of real template 47->49 with both rules present and idempotent on re-run. AC#4 (live pptx permission-prompt smoke test in fresh Documentation project) deferred for manual verification — example-skills:pptx plugin not in this repo, requires interactive Claude Code session; not automatable in autonomous loop. Precedent: sibling task-128/129 deferred equivalent live smoke-test ACs, accepted under reviewer rule R2. task-reviewer verdict: APPROVED (bf7520d) — all checklist items pass, R6/R11/R12/R13 spot-checks clean, AC#4 deferral accepted under R2. Reviewer additionally confirmed Dockerfile.install.docs already installs libreoffice-impress-nogui + poppler-utils (pdftoppm), so rules are functionally meaningful — no follow-up needed.
<!-- SECTION:NOTES:END -->
