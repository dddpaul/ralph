---
id: TASK-119
title: Distribute brainstorm-rules via ralph-init with section-based merge on upgrade
status: In Progress
assignee: []
created_date: '2026-05-11 11:22'
updated_date: '2026-05-11 11:28'
labels:
  - 'feature:ralph-init'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ship the canonical Ralph brainstorm rules (Save Design Conclusions Case A/B + Phase 4 Override) as a ralph-init template, with section-based ownership so user customizations survive upgrades.

## Design (option 1 selected from /how-to-distribute discussion)

**Section boundary:** The literal heading `## Project additions` divides the file. Everything ABOVE the heading is Ralph-managed (regenerated from template on upgrade). Everything FROM the heading onward (heading included) is user-owned (preserved verbatim on upgrade).

**Template structure:**

```markdown
## Save Design Conclusions (before Phase 4)
<canonical Ralph content>

---

## Phase 4 Override
<canonical Ralph content>

---

## Project additions

<\!-- Add project-specific brainstorm rules below this heading. Content here is preserved on \`ralph upgrade\`. -->
```

**Init flow:** copy template to `.claude/brainstorm-rules.md`; skip-if-exists (consistent with other init files).

**Upgrade flow:** section-aware merge. Algorithm:
1. Read existing `.claude/brainstorm-rules.md`.
2. Split at first occurrence of `## Project additions` heading (line-level exact match).
3. If heading found: replace everything ABOVE the heading with template's pre-heading content; keep the heading line + everything below verbatim.
4. If heading NOT found (legacy file, no convention yet): one-time migration — treat the entire existing file as user content; write the template's pre-heading content, then append a fresh `## Project additions` heading, then append the existing content verbatim below.
5. Write merged result back to `.claude/brainstorm-rules.md`.

**Self-consistency:** `.claude/brainstorm-rules.md` in this repo (the canonical source the template mirrors) ALSO gains the `## Project additions` section header — establishing the convention in the source-of-truth file.

## Source files

- `.claude/brainstorm-rules.md` — canonical Ralph rules content (current state to mirror into template)
- `skills/ralph-init/templates/claude/` — target directory for the new template file (already exists alongside `hooks/`, `settings.json`, `settings.local.json`)
- `skills/ralph-init/SKILL.md` — init flow (around Step 4 hooks-area) and upgrade flow (around line 285+ status table) to wire the new file
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 New file skills/ralph-init/templates/claude/brainstorm-rules.md exists and contains the canonical Save Design Conclusions (Case A + Case B) and Phase 4 Override sections matching the current .claude/brainstorm-rules.md byte-for-byte for the pre-heading portion
- [x] #2 skills/ralph-init/templates/claude/brainstorm-rules.md ends with a '## Project additions' section header followed by a one-line HTML comment explaining that content below the heading is preserved on ralph upgrade
- [x] #3 .claude/brainstorm-rules.md in this repo gains the same '## Project additions' section header (at the bottom, with the same explanatory HTML comment) — establishing the convention in the canonical source
- [x] #4 skills/ralph-init/SKILL.md init flow gains a step that reads templates/claude/brainstorm-rules.md and writes to .claude/brainstorm-rules.md, with skip-if-exists policy matching other init files
- [x] #5 skills/ralph-init/SKILL.md upgrade-status table (around lines 291-307) gains an entry for .claude/brainstorm-rules.md describing the merge semantics (e.g., 'managed via section-aware merge — pre-heading from template, post-heading preserved')
- [x] #6 After merge, running 'bash .claude/skills/ralph-sync/sync.sh classify' shows skill ralph-init as needing sync; after applying sync, the same command shows it as [unchanged]
- [x] #7 skills/ralph-init/SKILL.md upgrade flow documents the section-aware merge algorithm: split existing file at '## Project additions' heading; regenerate above from template; preserve heading+below verbatim; if heading is absent (legacy file lacking the convention), treat entire existing file as user content and append under freshly-added heading (one-time migration)
<!-- AC:END -->



## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan:
1. Add '## Project additions' section + HTML comment at end of .claude/brainstorm-rules.md (canonical source).
2. Copy resulting file to skills/ralph-init/templates/claude/brainstorm-rules.md.
3. Update skills/ralph-init/SKILL.md:
   - Add new init sub-step (3.9) to read template and write to .claude/brainstorm-rules.md with skip-if-exists.
   - Add entry in U2 status table (item 12) with merge semantics note.
   - Add merge algorithm in U4 special-merge section.
4. Verify ralph-sync classify shows ralph-init as [updated], apply sync, verify [unchanged].
<!-- SECTION:NOTES:END -->
