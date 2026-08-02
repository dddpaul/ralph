---
id: TASK-219
title: 'Fix OKF export frontmatter: strip from root md files, add to backlog docs'
status: To Do
assignee: []
created_date: '2026-08-02 09:24'
updated_date: '2026-08-02 09:25'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The okf-mcp-server exports a markdown file as an MCP resource iff its frontmatter has `export: true` AND a non-empty `type`; its default scan roots are design/, backlog/docs/, backlog/decisions/ (repo root is NOT a default root). Commit cf44bfe added OKF export frontmatter (export/title/type) to the three ROOT files README.md, CLAUDE.md, AGENTS.md — but repo root is not an okf scan root, so that frontmatter is dead weight there and is unwanted noise at the top of these files. Meanwhile the actual knowledge docs under backlog/docs/ (doc-1..doc-4) carry id/title/type/created_date but NOT export:true, so they are currently invisible to okf. Flip it to the intended policy: root md files have NO frontmatter and do not export; backlog docs export. Leave the 14 design/ docs exactly as-is (they keep exporting — user decision). This is a docs-only change; no code touched.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 README.md, CLAUDE.md, and AGENTS.md each start with document content (no leading YAML '---' frontmatter block)
- [ ] #2 The OKF keys export/title/type are removed from those three root files (grep for '^export:' returns none of them)
- [ ] #3 Each of backlog/docs/doc-1..doc-4 gains 'export: true' in its frontmatter while preserving its existing id/title/type/created_date keys (frontmatter still opens with '---' on line 1)
- [ ] #4 grep -rIl '^export:[[:space:]]*true' over *.md (excluding .git) lists all four backlog/docs files and NONE of README/CLAUDE/AGENTS
- [ ] #5 No file under design/ is modified by this change (git diff --name-only master..HEAD shows no design/ path)
- [ ] #6 Each backlog/docs export doc still has a non-empty 'type' (okf export gate: export:true + type both satisfied)
- [ ] #7 uv run ruff check . and uv run pytest both pass (docs-only change causes no regression)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) strip the export/title/type YAML frontmatter block from README.md, CLAUDE.md, AGENTS.md so each starts with its heading; (2) add 'export: true' to backlog/docs/doc-1..4 frontmatter, preserving id/title/type/created_date; (3) leave design/ untouched; (4) verify grep gate + ruff + pytest.

Deferred: task created for later; not implemented in this session per user request.
<!-- SECTION:NOTES:END -->
