---
id: TASK-222
title: Add markdown-prose no-hard-wrap convention to ralph-init docs templates
status: Done
assignee: []
created_date: '2026-08-09 08:22'
updated_date: '2026-08-09 10:56'
labels: []
dependencies:
  - TASK-220
  - TASK-221
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Docs/Mixed projects that ralph-init scaffolds as an Obsidian vault inherit a docs-conventions
template (`CLAUDE.conventions.docs.md`) whose **Markdown Standards** block tells authors to
"Wrap lines at 120 characters in source files". Hard-wrapping markdown PROSE to a column width
is an anti-pattern: a single newline inside a paragraph renders as a space in CommonMark
(Obsidian, Confluence), so the wraps change nothing in the rendered output but produce noisy
diffs (editing one word rewrites the whole block) and "chopped" text when reading the source.
This just bit a real docs project (stacks doc-9) and forced a full-document reflow (TASK-171).
The template must (1) stop instructing the anti-pattern, and (2) give both author and reviewer
the correct rule.

This is the THIRD docs-convention sibling alongside TASK-220 (Obsidian cross-links, R-DOCS-1)
and TASK-221 (terminology discipline, R-DOCS-2). It reuses the same `task-reviewer-rules.docs.md`
file and the ralph-init step that TASK-220 creates — this task only appends to them.

## Scope

In scope:
- In `CLAUDE.conventions.docs.md`: REMOVE the `- Wrap lines at 120 characters in source files`
  bullet from the **Markdown Standards** block (it contradicts the new convention), and add a
  `### Markdown prose line-wrapping` section (text below) after `### Code Style`.
- In `task-reviewer-rules.docs.md` (created by TASK-220 — dep): append rule `R-DOCS-3`
  (text below) at the end, after `R-DOCS-2` (added by TASK-221 — dep).

Out of scope:
- Do NOT create `task-reviewer-rules.docs.md`, add the ralph-init write step, or edit the Step 4
  file-list — TASK-220 owns those.
- Do NOT touch `CLAUDE.conventions.python.md` or Code-only behavior.
- Do NOT seed existing projects — templates for NEW projects only.
- Do NOT add a linter/hook that checks wrapping — text convention + reviewer rule only.

## Files

- `plugins/ralph/skills/ralph-init/templates/root/CLAUDE.conventions.docs.md` (exists) —
  remove the 120-column bullet from **Markdown Standards**; add `### Markdown prose line-wrapping`
  after `### Code Style`.
- `plugins/ralph/skills/ralph-init/templates/claude/task-reviewer-rules.docs.md`
  (created by TASK-220 — dep) — append `R-DOCS-3` at end of file, after `R-DOCS-2`.

## Convention text (insert verbatim into CLAUDE.conventions.docs.md, after `### Code Style`)

```
### Markdown prose line-wrapping

Prose in markdown documents is NOT hard-wrapped to a column limit.

- **One paragraph = one physical line.** Do not insert manual line breaks (real `\n`) inside a paragraph to hit a column width. Write the paragraph as one long line and let the editor soft-wrap it.
- **Why this is safe.** A single `\n` inside a paragraph renders as a space in CommonMark (Obsidian, Confluence), so removing hard wraps does NOT change the rendered output — only the source layout changes. Diffs stay clean (editing a paragraph touches one line, not the whole block) and the text is not "chopped up" by wraps when reading.
- **Still on their own lines, as before:** the blank line between paragraphs (paragraph separator), list items (one marker per item), table rows, headings, code fences, and blockquotes (one `>` per quote-paragraph). A hard break is forbidden only inside a prose paragraph.
```

And in the same file, in the **Markdown Standards** block, DELETE this bullet:

```
- Wrap lines at 120 characters in source files
```

## Reviewer rule text (append to task-reviewer-rules.docs.md, after R-DOCS-2)

```
## R-DOCS-3: Markdown prose no hard-wrap

Apply to any `.md` change that adds or edits prose. The source of truth is the "Markdown prose
line-wrapping" section in CLAUDE.md (do NOT duplicate it here). The reviewer must NOT require,
request, or itself introduce a hard mid-paragraph line break to satisfy a column limit — that
limit is code-only. Return CHANGES REQUESTED if the diff:

- inserts a hard newline inside a prose paragraph purely to wrap at a column width (a paragraph
  that was one physical line is split into several with no semantic reason);
- re-wraps an already-reflowed document back to a column limit.

Do NOT flag the legitimately multi-line structures (blank-line paragraph separators, list items,
table rows, headings, code fences, blockquote paragraphs) — only hard wraps inside a single
prose paragraph are a defect.
```

## Language note

The actual `CLAUDE.conventions.docs.md` file is written in English, so this task's inserts are
English to match (and to honor the "CLAUDE.md is English-only" rule from the source project).
Sibling tasks TASK-220 / TASK-221 currently specify Russian ("рабочий язык проекта") convention
text for the SAME English template file — the ralph owner may want to reconcile all three
siblings to one language when landing them.

## Source

Source: /Users/paul/Private/Alfa/Projects/standard/stacks@0f52058e967f
Source design context (read-only, do NOT modify): convention established in stacks — CLAUDE.md
section "Markdown prose line-wrapping" and `.claude/task-reviewer-rules.md` rule R-DOCS-3
(TASK-171, merged to master). The reflow that motivated it: stacks doc-9 reflowed from 454 to
263 physical lines, layout-only (content byte-equivalent, verified by a content-fingerprint gate).

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. TASK-220 AND TASK-221 — status Done: `task-reviewer-rules.docs.md` exists and already carries
   R-DOCS-1 and R-DOCS-2 (this task only appends R-DOCS-3). If either is not Done — STOP.
2. `(exists)` path `CLAUDE.conventions.docs.md` is present; it still contains the
   `Wrap lines at 120 characters in source files` bullet to remove, and a `### Code Style` block
   to insert after.
3. Each AC is objectively checkable (a grep over the two files).
4. Out-of-scope (template creation / init step / Step 4 edit, python conventions, Code-only,
   seeding existing projects) is untouched.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 In CLAUDE.conventions.docs.md the **Markdown Standards** block no longer contains the bullet 'Wrap lines at 120 characters in source files' (grep for '120 characters' returns nothing), and a '### Markdown prose line-wrapping' section is present after ### Code Style with the one-paragraph-per-line rule, the CommonMark space-rendering rationale, and the 'still on their own lines' list of structures.
- [x] #2 task-reviewer-rules.docs.md contains rule R-DOCS-3 'Markdown prose no hard-wrap' that references the 'Markdown prose line-wrapping' section in CLAUDE.md as the source of truth and does not duplicate its text.
- [x] #3 R-DOCS-3 lists the CHANGES REQUESTED conditions (a hard newline inside a prose paragraph purely to wrap at a column width; re-wrapping an already-reflowed document) and explicitly does NOT flag the legitimate multi-line structures (blank-line separators, list items, table rows, headings, code fences, blockquotes).
- [x] #4 This task does NOT create the reviewer-rules template, add a ralph-init write step, or edit the Step 4 file-list (owned by TASK-220); only the two existing files are edited.
- [x] #5 Code-only behavior and CLAUDE.conventions.python.md are unchanged; no existing projects are seeded.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) In templates/root/CLAUDE.conventions.docs.md remove the '- Wrap lines at 120 characters in source files' bullet from Markdown Standards, and append the '### Markdown prose line-wrapping' section verbatim at end (grouped after the TASK-221 Terminology section, matching the sibling pattern; all sit after ### Code Style). (2) In templates/claude/task-reviewer-rules.docs.md append 'R-DOCS-3: Markdown prose no hard-wrap' after R-DOCS-2, verbatim. English (per owner language-reconciliation note; text is already English), plain quotes, no hard-wrap of the long convention lines. (3) Gates: ruff + pytest, check ACs 1-5. (4) task-reviewer on git diff master..HEAD. (5) Done; merge with bump-version.sh --auto (shipped plugins/ralph/skills/** touched).

Commit: `0fa1d96` - task-222: add markdown prose no-hard-wrap convention + R-DOCS-3 to ralph-init docs templates

Done: Removed the '- Wrap lines at 120 characters in source files' bullet from Markdown Standards in templates/root/CLAUDE.conventions.docs.md and appended '### Markdown prose line-wrapping' (verbatim, English, long unwrapped lines — self-consistent with the rule it teaches) grouped after the TASK-221 Terminology section. Appended 'R-DOCS-3: Markdown prose no hard-wrap' after R-DOCS-2 in templates/claude/task-reviewer-rules.docs.md, pointing to the CLAUDE.md section as source of truth (no duplication). Only the two existing files edited; SKILL.md/ralph-init step/Step-4 list, python conventions, and existing projects untouched. Gates: ruff clean, pytest 346 passed. task-reviewer: APPROVED. Shipped plugins/ralph/skills/** touched -> version bump via bump-version.sh --auto at merge.

Commit: `a5bc6c9` - task-222: bump plugin version to 0.3.2 (patch)
<!-- SECTION:NOTES:END -->
