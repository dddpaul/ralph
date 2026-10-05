---
id: TASK-270
title: Fix the task-reviewer's override detection and working-tree scan
status: In Progress
assignee: []
created_date: '2026-10-05 16:41'
updated_date: '2026-10-05 17:01'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Post-merge re-reviews of TASK-262 and TASK-263, run under the task-reviewer's own new rules, each returned CHANGES REQUESTED with one blocking finding. Their original reviews scored 9 and 10 under the previous rules, because each task changed the agent that reviewed it. Both defects are still on master and were reproduced independently before filing. This task fixes them, fixes three minor wording findings, and records the post-merge evidence on the tasks it belongs to.

## B1 — override detection misses the forms rules files actually use

`plugins/ralph/agents/task-reviewer.md` line 81 builds the "override references" line with:

```bash
grep -oE 'replaces R(-[A-Z]+-)?[0-9]+' | sed 's/^replaces //'
```

Reproduced on master against the extracted pipeline:

```text
replaces R-DOCS-4                     -> R-DOCS-4
replaces `R-DOCS-4`                   -> none
Replaces R-DOCS-4.                    -> none
This rule replaces R5 and R-INFRA-3   -> R5          (R-INFRA-3 lost)
```

Rules files write IDs in backticks, and the agent's own Precedence section makes "a project rule that names a rule ID it replaces" the override mechanism, so a real override is most likely reported as `none`. That defeats the provenance line TASK-263 added for auditability. Recognise "replaces" case-insensitively, accept backticked and bare IDs, and report every ID named after "replaces" within the same sentence; an ID in a following sentence must not be captured, or ordinary cross-references become false overrides. Keep the pipeline portable to BSD grep, BSD sed and /bin/bash 3.2 (R-INFRA-3): macOS sed has no case-insensitive substitute flag, so do not rely on one. Update the prose that describes this line (currently "lists every rule ID that a loaded rule names after the word 'replaces'") to state the forms it recognises.

## B2 — R-CORE-5's scan reads the working tree, which R-CORE-1 forbids

R-CORE-1 (`task-reviewer.md` line 130) says "Base no finding on `ls`, `find`, `cat` or any other working-tree read". R-CORE-5's scan (line 159) greps the working-tree copy and makes any match blocking:

```bash
git diff master..HEAD --name-only -- 'backlog/tasks/*.md' | while IFS= read -r f; do
  grep -nE 'design/.*-brainstorm\.md' "$f" \
```

This matters in practice: CLAUDE.md commits the task file at Merge step (b), after review, so the copy on disk can differ from HEAD, and a task file the diff deletes makes grep fail on a missing path. Read committed content and skip deletions:

```bash
git diff master..HEAD --name-only --diff-filter=d -- 'backlog/tasks/*.md' | while IFS= read -r f; do
  git show HEAD:"$f" | grep -nE 'design/.*-brainstorm\.md' \
    && echo "R-CORE-5 violation: $f references a brainstorm file in its description"
done
```

## Minor findings still present on master

- M1: `task-reviewer.md` line 94 says to report applied tiers "at the top of the review", but the Report Format (line 204) now puts Rules provenance first and Custom rules applied second.
- M3: `README.md` line 345 lists blocking causes as "unmet AC, loaded-rule violation named by rule ID, correctness, bugs, security, unintended changes" and omits built-in rule violations, which the agent treats as blocking.
- M4: R-CORE-3 (`task-reviewer.md` line 147) says "a built-in rule is relaxed by a project rule that names its ID as replaced", narrower than Precedence, which lets any more specific tier replace a built-in rule.

A fourth minor finding from the 263 re-review (leftover "template" wording for the docs bundle) and a side observation from the 262 re-review (naming-guard.sh citing R5) were already fixed by TASK-265 and TASK-268 and are out of scope.

## Post-merge evidence to record

All of this was gathered in the interactive session after the merges and is not yet in any task file. Record it on this task's branch, since every change needs one.

TASK-263 AC #7, smoke-check half — the installed 0.11.0 ralph:task-reviewer ran its own loader snippet unedited and printed:

```text
plugin version: 0.11.0
docs bundle: /Users/paul/.claude/plugins/cache/dddpaul-ralph/ralph/0.11.0/skills/ralph-init/rules/task-reviewer-rules.docs.md
project root: /Users/paul/Private/Projects/ai/ralph
tier shared docs: not applied (docs_rules unset, no /Users/paul/Private/Projects/ai/ralph/.obsidian)
tier project: loaded (/Users/paul/Private/Projects/ai/ralph/.claude/task-reviewer-rules.md)
```

The bundle path exists (8875 bytes) and no line carried an unsubstituted plugin-root or project-root reference, so the Markdown-substitution mechanism works in a live agent. AC #7 can now be checked.

TASK-268 live check — after the plugin update, the installed 0.12.0 agent printed `plugin version: 0.12.0` and `tier shared infra: loaded (/Users/paul/.claude/plugins/cache/dddpaul-ralph/ralph/0.12.0/skills/ralph-init/rules/task-reviewer-rules.infra.md)`; both installed bundles are byte-identical to master.

Re-review verdicts — TASK-262: CHANGES REQUESTED, SCORE 5, blocking B2 above. TASK-263: CHANGES REQUESTED, SCORE 5, blocking B1 above. Both name this task as the fix.

## Limits

R-INFRA-2: this task edits the agent, so its own review runs under the pre-change agent, and a live check of the fixed pipeline is only possible after a push and a plugin update — record that as deferred. The extracted-snippet tests in `tests/unit/task-reviewer-rules-loading.bats` do execute the shipped snippet, so they are real behavioural evidence. BSD userland and /bin/bash 3.2 are only present on the macOS host; Ralph's Linux container has GNU tools and bash 5, so the portability half of AC #9 must be verified on the host before Done.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Override detection reports R-DOCS-4 for each of 'replaces R-DOCS-4', 'replaces `R-DOCS-4`' and 'Replaces R-DOCS-4.' — verified by tests in tests/unit/task-reviewer-rules-loading.bats that run the extracted loader
- [x] #2 Override detection reports every ID named after 'replaces' in the same sentence — 'replaces R5 and R-INFRA-3' and 'replaces `R5`, `R-INFRA-3`' both report R5 and R-INFRA-3 — and does not report an ID that appears only in a following sentence; verified by tests, with the agent's prose describing the recognised forms
- [x] #3 R-CORE-5's scan reads committed content with git show HEAD and skips files the diff deletes: a test shows a working-tree copy that differs from HEAD does not change the result and a task file deleted by the diff produces no error, and no working-tree grep remains in R-CORE-5
- [x] #4 plugins/ralph/agents/task-reviewer.md no longer tells the reviewer to report applied tiers 'at the top of the review'; the instruction points to the Report Format order, where Rules provenance comes first
- [x] #5 README.md's summary of blocking findings includes built-in rule violations alongside loaded-rule violations
- [x] #6 R-CORE-3's sentence on relaxing a built-in rule agrees with the Precedence section about which tiers may replace a built-in rule
- [x] #7 TASK-263 AC #7 is checked, and TASK-263's notes record the 0.11.0 smoke-check output quoted in this task's description
- [x] #8 TASK-262, TASK-263 and TASK-268 notes record their post-merge results from this task's description — the two re-review verdicts naming this task as the fix, and the 0.12.0 infra live check
- [ ] #9 Gates: uv run ruff check . is clean, uv run pytest passes, LC_ALL=C node_modules/.bin/bats tests/unit passes, and tests/unit/task-reviewer-rules-loading.bats also passes on the macOS host under BSD userland
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: B1 — replace the grep/sed override pipeline with a POSIX awk pass (tolower for case, no gensub/IGNORECASE) that, after stripping HTML comments, captures every R-ID after 'replaces' until the sentence ends (. ! ? before space/EOL, blank line, heading, new list item); document the forms. B2 — R-CORE-5 scan via --diff-filter=d + git show HEAD:. M1/M3/M4 wording. Tests: bats cases for override forms and an extracted R-CORE-5 scan run in a temp git repo. Record post-merge evidence on TASK-262/263/268.

Commit: `b4691f4` - task-270: detect overrides in every replaces form and scan committed task files in R-CORE-5

Gates in the Linux container: uv run ruff check . clean; uv run pytest 807 passed, 3 skipped; LC_ALL=C bats tests/unit 153 ok, 1 not ok — 'R11: settings.local.json keeps the template's JSON shape', which reads the git-ignored machine-local .claude/settings.local.json and fails identically on master with this diff stashed (environment, not this change). The six new bats cases fail against master's agent (verified by pointing AGENT at git show master:...) and pass on the branch. The container awk is mawk, so the override pipeline already runs on a non-GNU awk; it uses only POSIX awk (match/substr/tolower, no gensub/IGNORECASE/[[:class:]]) and no sed case-insensitive flag.

DEFERRED — AC #9 host half: BSD userland and /bin/bash 3.2 exist only on the macOS host; the one-true-awk source could not be fetched from the container. Before Done, run on the host: LC_ALL=C node_modules/.bin/bats tests/unit/task-reviewer-rules-loading.bats and record the result here. R-INFRA-2: a live check of the fixed agent needs a push and plugin update; deferred to after merge.

task-reviewer (ralph:task-reviewer, installed 0.12.0): APPROVED, SCORE 8 — 0 blocking, 2 minor: (1) an abbreviation like 'e.g. ' ends the sentence early, so later IDs are dropped (follows the documented sentence-end rule); (2) ';' and table-cell '|' do not end a sentence, so 'replaces R-CORE-6; see R-DOCS-2' also lists R-DOCS-2 (mitigated by 'Confirm each against the rule text'). Left as-is; candidates for a follow-up.

Not marked Done and not merged: the description requires the AC #9 host half (BSD userland, /bin/bash 3.2) to pass before Done. Remaining steps on the host: run LC_ALL=C node_modules/.bin/bats tests/unit/task-reviewer-rules-loading.bats, record the output, check AC #9, then Done + Merge step 6 (bump-version.sh --auto bumps the plugin version, since plugins/ralph/agents/task-reviewer.md changed).
<!-- SECTION:NOTES:END -->
