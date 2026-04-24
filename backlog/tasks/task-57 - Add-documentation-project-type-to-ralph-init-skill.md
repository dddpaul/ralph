---
id: TASK-57
title: Add documentation project type to ralph-init skill
status: To Do
assignee: []
created_date: '2026-04-24 15:16'
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
- [ ] #1 Q0 project type question added to SKILL.md with Code/Documentation/Mixed options
- [ ] #2 Documentation type skips Q1 and Q2, defaults to Python+Node
- [ ] #3 Dockerfile.lang.docs and Dockerfile.install.docs templates exist with python, uv, libreoffice-impress-nogui, poppler-utils, pptxgenjs
- [ ] #4 SKILL.md has Obsidian config step that copies app.json, hotkeys.json, snippets to .obsidian/
- [ ] #5 .gitignore includes Obsidian entries for docs projects
- [ ] #6 CLAUDE.conventions.docs.md template exists with docs-oriented conventions
<!-- AC:END -->
