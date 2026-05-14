---
id: TASK-121
title: Add pandoc to docs Dockerfile install fragment
status: In Progress
assignee: []
created_date: '2026-05-14 06:13'
updated_date: '2026-05-14 06:41'
labels:
  - 'feature:ralph-init'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
When ralph-init bootstraps a Documentation project (Q0 answer B, language=docs), the assembled Dockerfile installs libreoffice-impress-nogui, poppler-utils, build-essential, and pptxgenjs — but not pandoc. Documentation projects commonly need pandoc for format conversion (Markdown to PDF/DOCX/EPUB, etc.). Add it to the docs fragment.

## Source file

skills/ralph-init/templates/devcontainer/lang/Dockerfile.install.docs

Current apt-get list (line ~7):

```
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-impress-nogui \
    poppler-utils \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
```

Target:

```
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-impress-nogui \
    poppler-utils \
    build-essential \
    pandoc \
    && rm -rf /var/lib/apt/lists/*
```

## Scope

- Template-only change. Ralph's own .devcontainer is go-lang, not docs — does NOT need pandoc.
- No parity mirror needed (only one source file).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 skills/ralph-init/templates/devcontainer/lang/Dockerfile.install.docs apt-get install list contains the literal token 'pandoc' between 'build-essential' and the '&& rm -rf' line, preserving the existing backslash-continuation style
- [x] #2 grep -c '^\s*pandoc \\\\$' skills/ralph-init/templates/devcontainer/lang/Dockerfile.install.docs returns 1
- [x] #3 No other lang fragment files (node, python, go) are modified — diff scope is exactly the docs fragment plus the task markdown
- [ ] #4 After merge, bash .claude/skills/ralph-sync/sync.sh classify shows skill ralph-init as [unchanged] (post-sync)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Edit applied: skills/ralph-init/templates/devcontainer/lang/Dockerfile.install.docs gains 'pandoc' between 'build-essential' and the '&& rm' line. ACs 1-3 verified.
<!-- SECTION:NOTES:END -->
