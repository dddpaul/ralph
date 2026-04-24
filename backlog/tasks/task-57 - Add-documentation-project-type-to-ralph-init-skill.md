---
id: TASK-57
title: Add documentation project type to ralph-init skill
status: Done
assignee:
  - '@claude'
created_date: '2026-04-24 15:16'
updated_date: '2026-04-24 15:26'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a project type question (Q0) to ralph-init that gates the setup flow. When 'Documentation' is selected, skip build/lint/test questions, generate Obsidian vault config, use docs-specific Dockerfile with Python+Node+PPTX deps, and add docs-oriented CLAUDE.md conventions.

Context: ralph-init currently only supports code projects. Architecture/documentation projects use Obsidian for markdown editing and /pptx skill for presentations. They need Python (pptx generation) + Node.js (Claude Code) runtimes but no build/lint/test pipeline.

Implementation plan:

1. SKILL.md changes - add Q0 before existing questions:
   0. What type of project?
      A. Code — software project with build/lint/test
      B. Documentation — Obsidian vault, architecture docs, presentations
      C. Mixed — code + documentation
   When B selected: skip Q1 (language) and Q2 (quality checks), default to Python+Node. Q3 (devcontainer) and Q4 (AI tool) remain.

2. New Dockerfile templates (templates/Dockerfile.lang.docs and templates/Dockerfile.install.docs):
   - Dockerfile.lang.docs: FROM python:3.14 AS python-runtime (same as python template)
   - Dockerfile.install.docs: COPY python + uv from multi-stage, install libreoffice-impress-nogui, poppler-utils, build-essential, npm install -g pptxgenjs

3. New step in SKILL.md (3.8 or similar) for Obsidian config:
   - When project type is Documentation: copy templates/obsidian/app.json -> .obsidian/app.json, templates/obsidian/hotkeys.json -> .obsidian/hotkeys.json, templates/obsidian/snippets/ -> .obsidian/snippets/
   - Template files already exist in skills/ralph-init/templates/obsidian/

4. .gitignore additions for docs projects:
   .obsidian/workspace.json
   .obsidian/workspace-mobile.json
   .obsidian/plugins/
   .obsidian/community-plugins.json

5. New templates/CLAUDE.conventions.docs.md with docs-oriented conventions (no build/lint/test, markdown-focused workflow, presentation generation patterns)

6. CLAUDE.md template: when docs project, Project-Specific section should have no Build/Lint/Test entries or mark them as N/A

Files to create:
- skills/ralph-init/templates/Dockerfile.lang.docs
- skills/ralph-init/templates/Dockerfile.install.docs
- skills/ralph-init/templates/CLAUDE.conventions.docs.md

Files to modify:
- skills/ralph-init/SKILL.md (Q0, obsidian step, gitignore entries, dockerfile assembly for docs type)

Existing template files (already created):
- skills/ralph-init/templates/obsidian/app.json
- skills/ralph-init/templates/obsidian/hotkeys.json
- skills/ralph-init/templates/obsidian/snippets/wide-tables.css
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Q0 project type question added to SKILL.md with Code/Documentation/Mixed options
- [x] #2 Documentation type skips Q1 and Q2, defaults to Python+Node
- [x] #3 Dockerfile.lang.docs and Dockerfile.install.docs templates exist with python, uv, libreoffice-impress-nogui, poppler-utils, pptxgenjs
- [x] #4 SKILL.md has Obsidian config step that copies app.json, hotkeys.json, snippets to .obsidian/
- [x] #5 .gitignore includes Obsidian entries for docs projects
- [x] #6 CLAUDE.conventions.docs.md template exists with docs-oriented conventions
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: 1) Add Q0 project type question to SKILL.md before existing questions, with Code/Documentation/Mixed options. 2) Create Dockerfile.lang.docs and Dockerfile.install.docs templates (python runtime + libreoffice-impress-nogui, poppler-utils, pptxgenjs). 3) Create CLAUDE.conventions.docs.md with docs-oriented conventions. 4) Add step 3.8 Obsidian config to SKILL.md for copying obsidian templates. 5) Add .gitignore entries for Obsidian workspace files. 6) Update SKILL.md logic: Documentation type skips Q1/Q2, defaults to Python+Node; Mixed keeps all questions.

Commit: `c2cc6f0` - task-57: Documentation project type for ralph-init skill

Implemented documentation project type for ralph-init. Files created: Dockerfile.lang.docs, Dockerfile.install.docs, CLAUDE.conventions.docs.md. Files modified: SKILL.md (Q0 question, project type behavior, Obsidian config step 3.8, .gitignore entries, Dockerfile docs language, summary update).
<!-- SECTION:NOTES:END -->
