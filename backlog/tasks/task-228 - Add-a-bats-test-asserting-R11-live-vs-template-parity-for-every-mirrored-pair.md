---
id: TASK-228
title: Add a bats test asserting R11 live-vs-template parity for every mirrored pair
status: Done
assignee: []
created_date: '2026-09-03 20:45'
updated_date: '2026-09-04 05:08'
labels:
  - 'feature:task-filename-length-guard'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The task-reviewer caught template drift in TASK-227: `plugins/ralph/skills/ralph-init/templates/claude/hooks/naming-guard.sh` was mirrored from an intermediate version of `.claude/hooks/naming-guard.sh` and shipped a copy that failed this repo's own test suite. Nothing automated catches that class of defect — a grep over `tests/` finds no parity assertion for the R11 table in `.claude/task-reviewer-rules.md`.

Add a bats test (e.g. `tests/unit/template-parity.bats`) that walks the R11 live/template pairs and asserts each `diff` is silent. Pairs with documented carve-outs (`CLAUDE.md` generic section only; `.claude/task-reviewer-rules.md` excluded; `plugins/ralph/agents/*` excluded; `ralph.sh` / `refine.sh` shim-to-template only) need the carve-out encoded rather than skipped wholesale.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tests/unit/template-parity.bats exists and is picked up by 'bats tests/unit/'
- [x] #2 The test fails when any live/template pair in the R11 table diverges (verified by mutating one template copy)
- [x] #3 R11 carve-outs (CLAUDE.md generic-section-only, task-reviewer-rules.md, plugins/ralph/agents/) are encoded in the test rather than the whole pair being skipped
- [x] #4 The test passes on master with no source changes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: add tests/unit/template-parity.bats driven by an explicit pair registry (one 'live|template|mode' row per R11 table entry, plus two same-class rows the table omits: .claude/brainstorm-rules.md and git-hooks/pre-commit).

Modes:
- exact    — diff must be silent (settings.json, every mirrored .claude/hooks/*.sh, ralph.sh, refine.sh, devcontainer.json, init-firewall.sh, git-hooks/commit-msg, brainstorm-rules.md, git-hooks/pre-commit)
- region   — CLAUDE.md: compare only the region above '## Project-Specific'; every changed line must be justified by a documented allow-list entry (CARVE-OUT or DRIFT:TASK-NNN)
- prefix   — .git/hooks/post-commit: live must start with the template verbatim; the only permitted extra is the documented repo-local TASK-217 bump-version nudge block
- keys     — .claude/settings.local.json: gitignored per-developer override (absent in CI); assert template exists + same JSON top-level key set, never byte content

Carve-outs encoded as positive assertions rather than skips:
- .claude/task-reviewer-rules.md: assert NO templates/claude/task-reviewer-rules.md mirror exists (only the generic .docs.md variant)
- plugins/ralph/agents/*: assert templates/claude/agents/ does not exist and no agent has a template
- CLAUDE.md: assert both files carry the '## Project-Specific' boundary and the compared region is substantial (anti-vacuity)
- ralph.sh / refine.sh: shim-to-template only; assert the canonical orchestrators are NOT required to match

Closure checks so the registry cannot silently rot: every file under templates/ must be a registry row or a listed non-mirror (composition inputs, obsidian, docs variants); every .claude/hooks/*.sh must be a registry row or a listed repo-local hook.

Environment guard: .git/hooks/* and settings.local.json are untracked, so their content checks skip when the live file is absent (fresh CI checkout) — the template-side assertions still run.

Pre-existing drift found: templates/root/CLAUDE.md misses the ralph-task/ralph-prd sentence added by task-112 -> pinned as DRIFT:TASK-229 (filed) rather than fixed here, keeping AC #4 'passes with no source changes' true.

Commit: `015e183` - task-228: add a bats test enforcing R11 live-vs-template parity

Implemented tests/unit/template-parity.bats — 10 bats tests, picked up by 'bats tests/unit/' (now 105 unit tests total).

Design: an explicit pair registry of 'mode|live|template' rows, one per R11 table entry plus two same-class rows the table omits (.claude/brainstorm-rules.md, git-hooks/pre-commit). Four modes:
- exact  (15 rows) — diff must be silent; all drifted pairs are accumulated and reported with their diffs rather than aborting on the first
- region (CLAUDE.md) — only the text above '## Project-Specific'; every differing line must appear in claude_md_allowed_deviations, and every allow-list entry must still correspond to a real deviation, so the list is self-expiring instead of a growing exemption
- prefix (.git/hooks/post-commit) — live must open with the template verbatim; the only permitted tail is the repo-local TASK-217 bump-version nudge, matched line-shape by line-shape
- keys   (.claude/settings.local.json) — gitignored per-developer override, so JSON shape (top-level entries + permissions keys) is asserted, never bytes

Carve-outs are encoded as positive assertions, not skips: task-reviewer-rules.md asserts NO mirror exists and that the distinct generic .docs.md starter does; plugins/ralph/agents asserts no templates/claude/agents tree while at least 2 agents exist; the CLAUDE.md region boundary must exist on both sides with >=50 lines compared, and the project-local tail is asserted to still be an unfilled '<FILL IN' questionnaire so region scoping is load-bearing. Two closure tests stop the registry rotting: every file under templates/ must be a registry row or a listed non-mirror (composition inputs, obsidian, docs variants), and every file under .claude/hooks must be a registry row or a listed repo-local hook.

Environment: .git/hooks/* and settings.local.json are untracked and absent in a fresh CI checkout, so their content checks skip there while the template-side assertions still run. Verified green under that simulation.

AC #2 verified by mutation, 15 mutations total, every one killed except the intended negative control (a CLAUDE.md project-specific tail edit must stay allowed): template-side byte drift, live-side byte drift, deleted template, generic-region drift on either side, resolved-but-still-pinned deviation, post-commit mirrored-head drift, post-commit unmirrored tail, settings.local.json key loss, unregistered template file, unregistered template subtree, new live hook without a template, non-.sh live hook, a task-reviewer-rules.md mirror appearing, a templates/claude/agents tree appearing, and a canonical orchestrator smuggled into the registry.

Pre-existing drift found and deferred, NOT fixed here: templates/root/CLAUDE.md lacks the ralph-task / ralph-prd -> ralph-backlog sentence that task-112 added to the live CLAUDE.md. Filed as TASK-229 and pinned in the allow-list as DRIFT:TASK-229 with the reason inline. Deferred rather than fixed because the diff touches neither side of that pair and mirroring it changes shipped plugin content (version bump + its own review); the pin is byte-exact and self-expiring, so TASK-229 cannot land without also deleting it. Reviewer explicitly sustained the deferral.

Baseline note for future runs: this container's en_US.UTF-8 locale is broken and every bash invocation emits a 'bash: warning: setlocale' line that lands in bats' $output. That makes 3 tests fail on master too (bump-version nudge x2, filename-length-guard 125-byte) — all three assert [ -z "$output" ]. Run 'LC_ALL=C bats tests/unit/' for a true signal; all 105 pass there. The new tests are immune (they compare $status or captured stdout, never $output).

Review: task-reviewer APPROVED at 630a87e after one blocking fix — the drift accumulator's $(diff ...) took its exit status from diff, so bats' errexit aborted before the reporter ran, losing the filename and diff and stopping at the first drifted pair; fixed with '|| true'. Also applied 3 non-blocking nits: dropped an unused '(+)' notation, removed an over-strict 'ralph.sh must differ from refine.sh' assertion (R11 only says they are not required to match), and widened the hook closure scan from '*.sh' to -type f.

Gates: LC_ALL=C uv run ruff check . clean; uv run pytest 346 passed; LC_ALL=C bats tests/unit/ 105/105.
<!-- SECTION:NOTES:END -->
