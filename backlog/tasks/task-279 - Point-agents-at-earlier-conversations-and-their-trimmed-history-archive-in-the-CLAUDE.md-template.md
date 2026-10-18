---
id: TASK-279
title: >-
  Point agents at earlier conversations and their trimmed-history archive in the
  CLAUDE.md template
status: Done
assignee: []
created_date: '2026-10-18 06:58'
updated_date: '2026-10-18 09:30'
labels: []
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Agents asked to look up something from an earlier conversation do not know where Claude Code keeps its transcripts, and on the owner's machine part of that history no longer sits there: a local transcript trimmer (claude-trim, in the owner's dotfiles) cuts transcripts over 20 MB down to their last compaction, because Happy (the phone-control wrapper for Claude Code) re-reads the whole transcript every 3 seconds, and moves the full original into a gzipped archive. One bullet in the CLAUDE.md template's "Project Knowledge Sources" tells every Ralph project's agents where both are and how to search them, including gzipped files. The trimmer itself is not part of this repo.

## Scope

In scope:
- Add this bullet, verbatim, as the last item of "### Project Knowledge Sources" in the ralph-init CLAUDE.md template and in this repo's own CLAUDE.md:

```markdown
- Earlier conversations in this project: Claude Code keeps their transcripts in `~/.claude/projects/<dir>/*.jsonl`, where `<dir>` is the project's absolute path with every character other than a letter or digit replaced by `-`. If `~/.claude/transcript-archive/<dir>/` exists, a transcript trimmer has archived older history there as `*.jsonl.gz`. Search both with `rg -z <pattern>`.
```

- Bump the version per README "Releasing plugin updates" (a shipped template changes): both manifests to the same higher patch version.

Out of scope:
- The trimmer, its hooks or its archive layout (they live in the owner's dotfiles; the bullet only names the archive path).
- Any other change to the CLAUDE.md template or to ralph-init's upgrade logic; consumer projects pick the bullet up through the existing `ralph upgrade` drift path.
- A plugin, hooks or scripts for transcripts in this repo.

## Files

- `plugins/ralph/skills/ralph-init/templates/root/CLAUDE.md` (exists) — add the bullet to "### Project Knowledge Sources" (currently three bullets: README/`*.md`, `backlog doc list`, `CLAUDE.md`/`AGENTS.md`).
- `CLAUDE.md` (exists) — the same bullet in its "### Project Knowledge Sources".
- `plugins/ralph/.claude-plugin/plugin.json` (exists) — `version` bump.
- `.claude-plugin/marketplace.json` (exists) — `metadata.version` bump to the same value.

## Source

Source: /Users/paul/Private/Profile/.config/agterm@fab45241382b
Source design doc (read-only context, do NOT modify): /Users/paul/Private/Profile/.config/agterm/design/transcript-trim-brainstorm.md

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
- [x] #1 grep -cF "Earlier conversations in this project: Claude Code keeps their transcripts in" prints 1 for plugins/ralph/skills/ralph-init/templates/root/CLAUDE.md and 1 for CLAUDE.md, and in both files the bullet is the last item under "### Project Knowledge Sources", identical to the bullet in the description
- [x] #2 In both files the rest of "### Project Knowledge Sources" and every other section are unchanged: git diff master -- the two files shows only the added bullet line
- [x] #3 plugins/ralph/.claude-plugin/plugin.json version and .claude-plugin/marketplace.json metadata.version are equal and one patch above their values on master
- [x] #4 npm test and uv run pytest pass
- [ ] #5 The CLAUDE.md line in .claude/managed-file-drift.accept is regenerated with bash plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh accept . CLAUDE.md, and on the macOS host bash plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh check . exits 0 with no output; the output is recorded in the task notes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Handoff gate (destination): yellow, clarified with the user. Y1 — the bullet's naming rule was wrong: Claude Code replaces every character other than a letter or digit with '-', not only '/' and '.' (~/.claude/projects holds -Users-paul-Private-Alfa-Projects-af-comm for .../af_comm); the bullet in the description was corrected in place, and AC #1 checks against the corrected text. Y2 — .claude/managed-file-drift.accept pins CLAUDE.md's template and project hashes over the lines above '## Project-Specific', where Project Knowledge Sources sits, so the acceptance must be regenerated (new AC #5; its exit-0 check is host-only because in the container managed-file-drift.sh also reports the virtiofs-mounted .claude/settings.local.json). AC #3's patch bump is done at merge by .claude/hooks/bump-version.sh --auto (patch: no shipped file is added). Baseline: npm test on the macOS host already fails 7 on master (4 tee-buffering tests only under the host sandbox; 3 usage-pause preflight tests because uv run puts /opt/homebrew/bin ahead of the test's mock backlog) — AC #4 is judged against that baseline.

Plan: insert the verbatim bullet after the CLAUDE.md/AGENTS.md bullet in both CLAUDE.md files (python, exact-line insert), regenerate the CLAUDE.md accept line with managed-file-drift.sh accept, run npm test + uv run pytest, review, bump via bump-version.sh --auto at merge.

Commit: `a16ec83` - task-279: point agents at earlier conversations and the trimmed-history archive in CLAUDE.md

Commit: `a449ea3` - task-279: bump plugin version to 0.14.7 (patch)

Container verification: AC1 grep -cF prints 1/1, bullet is the last item in both files; AC2 git diff master on both files = one added line each; AC3 0.14.6 -> 0.14.7 in both manifests (bump-version.sh --auto). AC4 uv run pytest 913 passed/3 skipped, ruff clean; npm test 226/227 — the one failure (#155 R11 settings.local.json keeps the template's JSON shape) is the untracked, virtiofs-mounted .claude/settings.local.json, unrelated to this diff. AC5 accept regenerated: 'CLAUDE.md template=e75b750650519c53602bb8ce3152b2eb91f1ec1667b252c010aff1f41f97b611 project=1256bd43287397aaafb2c0e3da50dfd6c498e5fd88fa928562d4a784c80ea4d5'; in-container check prints only '.claude/settings.local.json: outdated' (rc=1, the expected container-only line); the macOS host exit-0 run is still owed by the owner.

Review: ralph:task-reviewer APPROVED (score 8, 0 blocking). Minor 1 (handoff 'Source design doc' line names an external brainstorm path) kept: it is the standard handoff Source block, outside this repo. AC #5 left unchecked on purpose: the accept line is regenerated and the in-container check reports only the host-mounted settings.local.json, but the macOS-host 'check . exits 0 with no output' run is still owed by the owner.
<!-- SECTION:NOTES:END -->
