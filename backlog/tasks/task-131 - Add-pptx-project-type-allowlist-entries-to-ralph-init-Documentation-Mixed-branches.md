---
id: TASK-131
title: >-
  Add pptx project-type allowlist entries to ralph-init (Documentation/Mixed
  branches)
status: To Do
assignee: []
created_date: '2026-05-19 08:45'
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
- [ ] #1 When project_type is Documentation or Mixed, ralph-init Step 3.7b (or equivalent gated sub-step) writes Bash(python scripts/office/soffice.py:*) and Bash(pdftoppm:*) to .claude/settings.local.json
- [ ] #2 When project_type is Code-only, neither pptx rule is added (verified by fixture init with Code project type)
- [ ] #3 Step 3.10 verification, when project_type is Documentation/Mixed, also checks both pptx rules and surfaces a WARN naming the missing one
- [ ] #4 Smoke test: in a fresh Documentation project, invoking example-skills:pptx workflow does not trigger a permission prompt for the python soffice or pdftoppm commands
<!-- AC:END -->
