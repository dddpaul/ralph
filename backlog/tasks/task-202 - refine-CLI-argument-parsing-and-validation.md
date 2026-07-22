---
id: TASK-202
title: refine CLI argument parsing and validation
status: Done
assignee: []
created_date: '2026-07-22 16:29'
updated_date: '2026-07-22 16:58'
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
- [x] #1 Parses --prompt, --draft, --author, --reviewer, --type, --tool, --model, --effort, --timeout, --max-iterations, --threshold, --output-dir, --on-error, --retry-count, --devcontainer, --resume, --verbose, --dry-run
- [x] #2 Defaults match refine.sh: type=md, tool=claude, model=claude-opus-4-8, effort=medium, timeout=15, max-iterations=10, threshold=8, output-dir=iterations/, on-error=stop, retry-count=2
- [x] #3 --prompt and --draft are mutually exclusive; exactly one is required (violation prints an error and exits 1)
- [x] #4 --author and --reviewer are required; a missing role file prints an error and exits 1
- [x] #5 Invalid --type (not md|drawio|puml), --effort (not low|medium|high|max), --on-error (not stop|continue|retry), --threshold (outside 1-10), --timeout/--max-iterations (<1), or --retry-count (<0) each print an error and exit 1
- [x] #6 pytest covers each validation branch in test_refine_args.py
- [x] #7 uv run pytest and uv run ruff check . pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Add ralph/refine/args.py mirroring ralph/args.py (ParsedArgs frozen dataclass, build_parser/parse/validate). Flags: --prompt --draft --author --reviewer --type(dest artifact_type) --tool --model --effort --timeout --max-iterations --threshold --output-dir --on-error --retry-count --devcontainer --resume --verbose --dry-run. Defaults: type=md tool=claude model=claude-opus-4-8 effort=medium timeout=15 max-iterations=10 threshold=8 output-dir=iterations/ on-error=stop retry-count=2. validate() returns None|error-str (first-failure-wins), exit 1 via cli.main: prompt/draft mutually exclusive + exactly-one required; author/reviewer required + readable; type in md|drawio|puml; effort in low|medium|high|max (4, no xhigh); on-error in stop|continue|retry; threshold 1-10; timeout>=1; max-iterations>=1; retry-count>=0; tool in claude|opencode (parity w/ reused ralph.tools). Wire cli.main to parse+validate+print-err+return 1 (mirror ralph_orchestrator.main); loop dispatch deferred to US-005. Tests: tests/test_refine_args.py covering every branch + defaults + parse. Gate: uv run pytest && uv run ruff check . (note refine.sh absent in repo; PRD/AC are defaults source of truth).

Commit: `b6fa050` - task-202: refine CLI argument parsing and validation (US-002)

Done (task-reviewer APPROVED). Added ralph/refine/args.py (RefineArgs frozen dataclass + build_parser/parse/validate) mirroring ralph/args.py: choices validated in validate() not argparse so violations exit 1 with parity 'Error: ...' messages (first-failure-wins). cli.main wires parse+validate (mirrors ralph_orchestrator.main); loop dispatch deferred to US-005 (returns 0 on valid args). Notable: --effort is low|medium|high|max (4, NO xhigh) per AC #5, differing from ralph's args by design; --type uses dest=artifact_type (type builtin); int flags use type=int so non-numeric -> argparse exit 2, range checks (<1, 1-10, >=0) in validate() -> exit 1; --tool validated vs claude|opencode as parity superset with reused ralph.tools layer (tested). prompt/draft file existence NOT validated (AC only requires author/reviewer readability). refine.sh absent in repo -> defaults sourced from PRD+AC (agree). Gate: uv run pytest 233 passed (+29 test_refine_args.py), uv run ruff check . clean, pyright 0 errors on refine/.
<!-- SECTION:NOTES:END -->
