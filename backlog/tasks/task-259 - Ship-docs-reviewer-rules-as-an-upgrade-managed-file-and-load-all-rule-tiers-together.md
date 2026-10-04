---
id: TASK-259
title: >-
  Ship docs reviewer rules as an upgrade-managed file and load all rule tiers
  together
status: Done
assignee: []
created_date: '2026-10-04 17:33'
updated_date: '2026-10-04 18:09'
labels:
  - 'feature:ralph-init'
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Documentation / Mixed projects receive the docs reviewer rules from `templates/claude/task-reviewer-rules.docs.md` exactly once. ralph-init writes the template into `.claude/task-reviewer-rules.md` only when that file is missing, and upgrade never touches it again (Init Step 3.7c, Upgrade item 15). The project then appends its own rules to the same file, so the shared part and the project part can no longer be told apart, and no later improvement to the template reaches any existing project.

On the source machine this split four documentation projects into four unrelated rule files (94, 160, 38 and 26 lines; two pairs of projects share no rule at all). Projects that already had a rules file before init never received R-DOCS-1..3. Rules proven in one project — closing a "text fits" criterion only with a correctly rendered crop, keeping measurement comments in sync with the measured text, document self-consistency, consistency between a document and its derived deck/diagrams — never reached the others. The same review remark had to be given to each project separately.

The agent cannot combine tiers either: `plugins/ralph/agents/task-reviewer.md` loads `.claude/task-reviewer-rules.md` OR `~/.claude/task-reviewer-rules.md` (`if … elif`), never both.

## Scope

In scope:
- A managed shared file in Documentation / Mixed projects: `.claude/task-reviewer-rules.docs.md`, generated from `templates/claude/task-reviewer-rules.docs.md`. Init writes it; Upgrade overwrites it from the template every time. Its first lines say it is managed by ralph-init, is overwritten on upgrade, and that project rules belong in `.claude/task-reviewer-rules.md`.
- `.claude/task-reviewer-rules.md` stays project-owned: Init no longer copies the docs template into it; Upgrade still never touches it.
- task-reviewer loads every non-empty tier, additively, in this order: `~/.claude/task-reviewer-rules.md` (user-global), `.claude/task-reviewer-rules.docs.md` (shared docs rules), `.claude/task-reviewer-rules.md` (project). It reports every applied tier at the top of the review. When a project rule explicitly names a shared rule ID it replaces, the project rule wins.
- Extend the docs template with the rules below. They are already in use in downstream projects; the texts here are generalized so they carry no project, document or domain names.
- The `.gitignore` block in ralph-init re-includes the new file next to `!.claude/task-reviewer-rules.md`.
- Upgrade prints a one-line hint when the project file still repeats a heading that now lives in the managed file (projects that got R-DOCS-1..3 copied at init), so the owner can delete the duplicate.

Rules to add to the template. Keep R-DOCS-1..3 numbering; adapt wording to the template's style, keep the substance:

```text
R-DOCS-1 addition: in prose (outside tables) a wiki-link's display pipe needs no escaping, and the reviewer MUST NOT demand it there.

R-DOCS-2 addition: task titles and task-<id> branch names stay ASCII English where a naming hook enforces it; the reviewer MUST NOT demand that an English title be translated into the working language.

R-DOCS-4: Markdown document consistency.
When the diff touches any backlog/docs/**/*.md or design/**/*.md file:
1. Read the full HEAD version of each modified .md file, not just the diff.
2. Verify the new/changed content does not contradict previously stated assumptions/base statements, fixed criteria or pre-decided values, impossibility statements, or quantitative claims (counts, sums) that must stay consistent across sections.
3. If the change revisits a previously closed question, the reframing must be explicit, not a silent re-fork.
4. Cross-section terminology drift is a defect: the same concept uses the same term throughout the document.
Any contradiction or drift -> CHANGES REQUESTED naming the conflicting section/line.

R-DOCS-5: Consistency across a document family.
A document family is a canonical document plus its derived artifacts, identified by a shared document id in the path or filename, e.g. backlog/docs/doc-N*.md, design/doc-N-*.md, presentations/doc-N/**, drawio/** and puml/** files naming doc-N. When the diff touches two or more artifacts of one family, verify across them: identifier alignment (names/numbers of sections, patterns, components), dimension alignment (fixed value sets use the same vocabulary), quantitative claims (counts and sums match). A change to one artifact without the corresponding update to the others is a defect — flag missing updates. A project may define its families more precisely in its own rules file.

R-DOCS-6: A fit criterion is closed by a raster crop plus a slack number.
Applies to any acceptance criterion claiming text stays inside a frame, card or slide edge in a built deck.
- The criterion MUST NOT be marked done unless a raster crop of that area, taken from the BUILT artifact, is attached to the task notes (soffice --headless --convert-to pdf, then pdftoppm -png -r 220 -f <N> -l <N>, cropped to the area). No crop -> reject, however convincing the diff looks.
- A crop is only as honest as the fonts under it. For every font family the deck declares, run fc-match -f '%{family[0]} | %{file}\n' for regular and bold: the family MUST be the one declared (or a documented metric-compatible twin), and regular and bold MUST come from different files. Family alone misses a variable font without a static bold (bold drawn at regular weight, text looks narrower); distinct files alone misses substitution (a host serving another family, text looks wider). Both errors were observed.
- The crop is necessary, not sufficient: read it with a slack number computed as the volume of text per box against the box's line capacity, not the length of the longest line. A block rendering N lines into room for exactly N lines overflows on any metric disagreement, including the presenting machine's fonts. Ask for the slack number whenever the crop shows a block at its line capacity.
- A declared height in the source is a layout cache that the presentation software re-autofits; a number in the diff proves nothing.
Why three steps: in one project four consecutive tasks closed a fit criterion and were APPROVED on renders made with the wrong fonts; text was later cut that never needed cutting.

R-DOCS-7: A measurement in a comment belongs to the text it measured.
When a change edits text whose size, fit or wording a nearby comment measures or justifies, that comment MUST be updated in the same change. The reviewer reads the comments around every edited block and rejects the change when one still describes the old text.
- Check by grep: take the numbers and distinctive phrases from comments in the changed region and search the repository after the edit; every hit still describing superseded text is a defect (hits in completed tasks' notes are history, leave them).
- Every measurement written into a comment MUST name the edition it belongs to (the task that produced it or the wording it measured).
- Covers any comment whose truth depends on the text beside it: a rationale for a cut, a count of occurrences, a claim that a block is the tightest.

R-DOCS-8: Publication is never implicit.
Publishing a document outside the repository — to a wiki, a shared drive, a chat channel or any
external service — is a separate action that a task must ask for in its own words. A task that
writes or edits a document does not authorize publishing it, and the reviewer MUST NOT treat an
unpublished document as unfinished work or ask for publication the task did not request. Return
CHANGES REQUESTED when a diff performs or automates an external publication outside the task's
stated scope. When the task does ask for publication, it is in scope and this rule does not apply.
A project may be stricter (for example requiring a named approver); it may not be looser.

R-DOCS-9: The review report is written in the project's working language.
The "Terminology discipline" section in CLAUDE.md requires the project's documents and an agent's
own answers to use the working language. This rule applies that to the one output the reviewer
itself writes: the review report. Rule IDs, file paths, command names, identifiers and quoted code
or output stay verbatim, and headings stay English where a naming hook enforces it (see R-DOCS-2).
A report written in another language is the reviewer's own defect to fix before returning it, never
a finding against the author.
```

Out of scope:
- Editing any downstream project's rules file — each project trims its own file in a follow-up task after upgrading.
- Project-specific rules (a classification corpus run, rules naming a concrete document number or domain term).
- Changing the task-reviewer checklist or report format — a separate task (evidence per AC and a score).
- Code-only projects: they get no docs file, as today.
- Moving the user-global tier or creating `~/.claude/task-reviewer-rules.md`.

## Files

- `plugins/ralph/agents/task-reviewer.md` (exists) — "Custom Rules Loading" section: additive three-tier loading and the tier report; the frontmatter description mentions the tiers.
- `plugins/ralph/skills/ralph-init/templates/claude/task-reviewer-rules.docs.md` (exists) — managed header and the rule additions above.
- `plugins/ralph/skills/ralph-init/SKILL.md` (exists) — Init Step 3.7c, the created-files listing, Upgrade item 15, the Upgrade write rule for `.claude/task-reviewer-rules.md`, and the `.gitignore` re-include block.
- `tests/unit/template-parity.bats` (exists) — the "R11: task-reviewer-rules.md is project-specific" test references the docs template; keep it true and cover the new managed file.
- a test under `tests/` (to-create) — runs the loading snippet from the agent file against fixture files.

## Source

Source: /Users/paul/Private/Alfa/Projects/standard/stacks@4691afcfd3b0
The rule texts above are condensed from the reviewer rules files of four downstream documentation projects on the source machine; those files are outside this repo and not readable from the devcontainer, so everything needed is inlined here.

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, build command, or visible behavior — not "works correctly").
3. All dependencies in the task's frontmatter are status=Done.
4. Out-of-scope items are not accidentally pulled in by ambiguous AC.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 templates/claude/task-reviewer-rules.docs.md opens with a header saying it is managed by ralph-init, is overwritten on upgrade, and that project rules belong in .claude/task-reviewer-rules.md — verified by grep
- [x] #2 The template contains R-DOCS-4 (document consistency), R-DOCS-5 (document family consistency), R-DOCS-6 (fit criterion closed by a crop with verified fonts plus a slack number) and R-DOCS-7 (measurement comments), plus the R-DOCS-1 addition (no pipe-escaping demand outside tables) and the R-DOCS-2 addition (English titles where a naming hook enforces them) — verified by grep for each
- [x] #3 The template names no downstream project and no task ID — grep for stacks, services, channels, core and TASK-[0-9] over the template returns nothing
- [x] #4 ralph-init SKILL.md Init Step 3.7c writes the template to .claude/task-reviewer-rules.docs.md for Documentation / Mixed projects and no longer writes it into .claude/task-reviewer-rules.md — verified by grep
- [x] #5 ralph-init SKILL.md Upgrade overwrites .claude/task-reviewer-rules.docs.md from the template on every upgrade, still never touches .claude/task-reviewer-rules.md, lists the new file in the status table, and prints a hint when the project file repeats a heading present in the managed file — verified by grep
- [x] #6 The .gitignore block in ralph-init SKILL.md re-includes !.claude/task-reviewer-rules.docs.md — verified by grep
- [x] #7 task-reviewer.md loads every non-empty tier additively in the order user-global, .claude/task-reviewer-rules.docs.md, .claude/task-reviewer-rules.md, reports every applied tier, and states that an explicit project override of a named shared rule wins — verified by a new test that runs the loading snippet from the agent file against fixture files in a temp dir and asserts all three contents appear in that order
- [x] #8 tests/unit/template-parity.bats covers the new managed file; uv run ruff check . is clean, uv run pytest passes and LC_ALL=C bats tests/unit passes
- [x] #9 The template contains R-DOCS-8 (publication is never implicit, with the in-scope carve-out when a task asks for it) and R-DOCS-9 (the review report uses the project's working language, identifiers and quoted output verbatim) — verified by grep for each
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Design provenance (checked before starting, not yet implemented). Source design: stacks design/harness-improvement-brainstorm.md at 4691afc — this task is proposal P2, TASK-260 is P1. The design's order is P2, then P1, then P3, which matches the 259<-260 dependency.

Divergence from P2 point 1, deliberate. The design puts the shared rules in the user-global ~/.claude/task-reviewer-rules.md ("сначала общий ~/.claude/task-reviewer-rules.md, потом проектный"). This task instead ships a plugin-managed per-project .claude/task-reviewer-rules.docs.md and scopes out the user-global file, while keeping that tier first in the load order, so "reads both" holds and becomes three tiers. Rationale: the design's own distribution section asks for "шаблон в ralph-init и проверка совпадения с шаблоном", and a template is what a managed file provides. Costs of the divergence, to weigh rather than ignore: upgrade/version skew between projects; docs defaults unavailable to Code-only projects that do occasional documentation work; and no stated precedence rule for a conflict between the user-global tier and the managed tier (the task defines only that a project rule naming a shared rule ID wins).

P2's seven shared-rule categories, mapped against the template at HEAD (verified by reading it, not inferred):
1. response language — present as a convention in CLAUDE.conventions.docs.md ("The documents in this project (and your own answers) are written in the project's working language"); NOT an explicit reviewer rule about the reviewer's own report -> partial
2. Obsidian links, pipe escaped in tables — R-DOCS-1 plus this task's addition -> covered
3. no transliteration + exceptions list — R-DOCS-2 (forbids transliteration into the working language's alphabet; "Do NOT flag the project's keep-list terms") -> covered, and generalized beyond the design's Cyrillic-specific wording
4. no hard wrap inside a paragraph — R-DOCS-3 "Markdown prose no hard-wrap" -> covered
5. publication is not part of the task — ABSENT, no rule covers it
6. fit check by image with correct fonts — R-DOCS-6 (added here) -> covered
7. measurements in comments updated with the text — R-DOCS-7 (added here) -> covered
So five of seven are covered, response language is partial, publication is the one genuine gap.

R-DOCS-4 (document consistency) and R-DOCS-5 (document family consistency) appear nowhere in P2's list. They are additional requirements of this task, which states they are already in use in downstream projects. Recorded as that verified fact; no rationale beyond it is claimed.

AC #8 limit. This repo is Code-only (no .obsidian/), so .claude/task-reviewer-rules.docs.md can never exist here and an unconditional exact-parity row fails at tests/unit/template-parity.bats:152-161 with "missing live file for <tmpl>" (only .git/hooks/* is exempted). AC #8 is therefore satisfied by keeping claude/task-reviewer-rules.docs.md in non_mirrored_templates with an explanatory comment and asserting the three managed-header promises; the "generic starter" comment at :449-450 needs updating because the docs template becomes a managed tier rather than a starter. Do not manufacture a live docs file to make a pair pass.

What AC #8 does NOT deliver, to be stated as a limit rather than glossed: overwrite-on-upgrade is synchronization, not drift-impossibility. It restores parity at a successful upgrade; nothing detects drift between upgrades, and post-upgrade edits, plugin-version skew, skipped upgrades and misexecution of the install step all produce drift. Misexecution is a live source, not a theoretical one: Init 3.7c contains zero fenced code blocks (counted between the 3.7c and 3.8 headings), so the write is prose carried out by an agent and no test can prove the destination. The design asks for "проверка совпадения с шаблоном"; this task does not provide a downstream drift detector.

Scope addition, user-approved 2026-10-04: added R-DOCS-8 (publication never implicit) and R-DOCS-9 (review report in the project's working language) to close the two gaps the P2 mapping above identified — publication absent, response language partial. R-DOCS-8 is phrased narrowly on review advice: a blanket 'publication is never part of a task' would collide with explicitly authorized publish work (this environment ships a publish skill), so the rule bans implicit publication and carves out tasks that request it, with projects free to be stricter. R-DOCS-9 covers the reviewer's own report, which CLAUDE.conventions.docs.md did not reach — it governs documents and an agent's answers, but no rule named the review report itself. New AC #9 makes both greppable. P3 (frozen examples, channels first) stays unfiled by decision, not oversight.

Plan: managed header + R-DOCS-1/2 additions + R-DOCS-4..9 in the docs template; task-reviewer loads three tiers additively via a loop (user-global, shared docs, project) and reports them; ralph-init Init 3.7c writes .claude/task-reviewer-rules.docs.md unconditionally and never the project file; Upgrade item 15 overwrites the managed file, never touches the project file, prints a duplicate-heading hint; .gitignore re-include; new tests/unit/task-reviewer-rules-loading.bats extracts and runs both snippets against fixtures; template-parity gains a managed-header test.

Commit: `aacb97a` - task-259: ship docs reviewer rules as a managed tier and load all rule tiers additively

Commit: `15bac81` - task-259: guard the duplicate-heading hint on both rule files

Done. Template: managed header (lines 1-3), R-DOCS-1/2 additions, R-DOCS-4..9. Agent: loop over three tiers, additive, tier list reported, explicit project override of a named rule ID wins. ralph-init: 3.7c writes .claude/task-reviewer-rules.docs.md unconditionally and never the project file; U2 item 15 + write rule overwrite the managed file, project file untouched, portable duplicate-heading hint snippet guarded on both files; .gitignore re-include in the template block and the repo's own .gitignore. Tests: tests/unit/task-reviewer-rules-loading.bats extracts and runs the agent loader and the upgrade hint snippet against fixtures; template-parity.bats keeps the docs template non-mirrored (Code-only repo) and asserts the managed header. Gates: ruff clean, pytest 699 passed, bats tests/unit 119/119 in a clean worktree (in /workspace the settings.local.json shape test fails on the gitignored per-developer file, identically on master). task-reviewer APPROVED; took nit 1 (guard), left nit 2 (U5 table column one char short) and the documented user-global vs shared-docs precedence gap. Limit: overwrite-on-upgrade synchronizes at upgrade time only; no downstream drift detector.

Commit: `5f84f60` - task-259: bump plugin version to 0.9.1 (patch)
<!-- SECTION:NOTES:END -->
