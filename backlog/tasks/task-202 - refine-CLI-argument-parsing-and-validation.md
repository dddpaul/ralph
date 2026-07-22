---
id: TASK-202
title: refine CLI argument parsing and validation
status: To Do
assignee: []
created_date: '2026-07-22 16:29'
labels:
  - 'feature:ralph-refine'
dependencies:
  - TASK-201
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
US-002 of ralph-refine. Parse and validate the full refine.sh flag set with matching defaults, so existing invocations keep working. See design/ralph-refine-prd.md US-002.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Parses --prompt, --draft, --author, --reviewer, --type, --tool, --model, --effort, --timeout, --max-iterations, --threshold, --output-dir, --on-error, --retry-count, --devcontainer, --resume, --verbose, --dry-run
- [ ] #2 Defaults match refine.sh: type=md, tool=claude, model=claude-opus-4-8, effort=medium, timeout=15, max-iterations=10, threshold=8, output-dir=iterations/, on-error=stop, retry-count=2
- [ ] #3 --prompt and --draft are mutually exclusive; exactly one is required (violation prints an error and exits 1)
- [ ] #4 --author and --reviewer are required; a missing role file prints an error and exits 1
- [ ] #5 Invalid --type (not md|drawio|puml), --effort (not low|medium|high|max), --on-error (not stop|continue|retry), --threshold (outside 1-10), --timeout/--max-iterations (<1), or --retry-count (<0) each print an error and exit 1
- [ ] #6 pytest covers each validation branch in test_refine_args.py
- [ ] #7 uv run pytest and uv run ruff check . pass
<!-- AC:END -->
