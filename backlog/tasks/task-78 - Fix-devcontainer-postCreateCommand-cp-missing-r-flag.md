---
id: TASK-78
title: Fix devcontainer postCreateCommand cp missing -r flag
status: Done
assignee: []
created_date: '2026-05-01 13:18'
updated_date: '2026-05-01 13:23'
labels:
  - devcontainer
  - bug
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The postCreateCommand in .devcontainer/devcontainer.json (line 61) and the matching template at skills/ralph-init/templates/devcontainer.json runs:

    cp /workspace-host-claude/* /workspace/.claude/

Without -r, this fails on subdirectories. Our .claude/ now contains agents/ and hooks/ directories (mirrored from the host into /workspace-host-claude/), so the bare cp emits 'cp: -r not specified; omitting directory "…/agents"' and exits non-zero, which kills postCreateCommand and skips downstream init steps.

Same failure was observed in another project running this template.

Fix: replace with 'cp -a /workspace-host-claude/. /workspace/.claude/' so subdirectories are copied recursively, attributes are preserved, and dotfiles (which the bare * glob skips) are included. Apply the change to both files.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 cp in postCreateCommand uses -a (or -r) so subdirectories under /workspace-host-claude/ are copied
- [x] #2 Form 'cp -a /workspace-host-claude/. /workspace/.claude/' is used so dotfiles are also copied
- [x] #3 Fix applied to both .devcontainer/devcontainer.json and skills/ralph-init/templates/devcontainer.json
- [x] #4 Manual smoke test: rebuild devcontainer; postCreateCommand exits 0; /workspace/.claude/agents/ and /workspace/.claude/hooks/ are present inside the container
- [x] #5 Existing behaviour preserved: jq sandbox.enabled=false patch on settings.local.json still runs and succeeds
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Replace 'cp /workspace-host-claude/* /workspace/.claude/' with 'cp -a /workspace-host-claude/. /workspace/.claude/' in both .devcontainer/devcontainer.json and skills/ralph-init/templates/devcontainer.json. The -a flag handles subdirectories recursively and preserves attributes, and the /. source form includes dotfiles.

Commit: `fb12733` - task-78: Use cp -a in postCreateCommand to copy subdirectories and dotfiles

AC#4 verified via simulated smoke test (cp -a correctly copies subdirs and dotfiles). Full devcontainer rebuild requires manual verification.
<!-- SECTION:NOTES:END -->
