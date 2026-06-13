---
id: TASK-139
title: Reorder ralph-init hook activation and widen master-branch-guard exempt list
status: Done
assignee: []
created_date: '2026-06-13 17:20'
updated_date: '2026-06-13 17:37'
labels:
  - 'feature:ralph-init-hook-ordering'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ralph-init self-blocks when run on an existing project with an Obsidian vault. Step 3.7a in `skills/ralph-init/SKILL.md` writes the project-wide settings.json — the file that registers Claude Code hooks — which activates `.claude/hooks/master-branch-guard.sh` mid-session. Step 3.9 then writes .obsidian config files and is denied because the hook only exempts three patterns: .claude/, design/, and the .gitignore basename.

Two-axis fix:

1. Reorder ralph-init so the activation trigger (the project-wide settings.json) is the last write of the bootstrap. Split Step 3.7a — keep the hook script writes and `.claude/settings.local.json` in the early slot; move only `.claude/settings.json` to a new Step 3.11 placed after current Step 3.10.

2. Widen the master-branch-guard exempt block to also pass through editor/vault config directories that users legitimately edit on master without opening a task branch.

Locked exempt list (Q1, six dirs to add to the exempt case statement):

```
.obsidian/
.vscode/
.idea/
.cursor/
.zed/
.fleet/
```

Each must follow the same exempt-pattern style already used for .claude/ and design/ — both shapes:

```
case "$path" in */<dir>/*|<dir>/*) exit 0;; esac
```

Existing master-branch-guard tests live in `tests/unit/pretools-hooks.bats` (lines 121–156). The new exempt-case tests go there too — one positive case per new dir.

Design conclusions in `design/ralph-init-hook-ordering-brainstorm.md` (Options A–E walked, Option C = A+B locked, addendum 2026-06-13).

Upgrade-mode latent bug (Q4 in the brainstorm) is filed as a SEPARATE sibling task — not bundled here.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `.claude/hooks/master-branch-guard.sh` exempt block widens to also pass through six editor/vault dirs (.obsidian/, .vscode/, .idea/, .cursor/, .zed/, .fleet/), each in both */dir/* and dir/* shapes matching existing exempt-pattern style at lines 29-30
- [x] #2 Header comment block of `.claude/hooks/master-branch-guard.sh` (lines 2-3) updated to enumerate the new exempts so a reader sees the full exempt set without grepping the case statement
- [x] #3 `skills/ralph-init/templates/claude/hooks/master-branch-guard.sh` is byte-identical to live `.claude/hooks/master-branch-guard.sh` (R11 parity verified by diff producing no output)
- [x] #4 `skills/ralph-init/SKILL.md` Step 3.7a is split: writing .claude/hooks/*.sh and `.claude/settings.local.json` remains in the early slot; writing `.claude/settings.json` is removed from 3.7a
- [x] #5 `skills/ralph-init/SKILL.md` adds a new Step 3.11 placed after current Step 3.10 that writes `.claude/settings.json` from `skills/ralph-init/templates/claude/settings.json`; body includes one-line rationale plus back-pointer to `design/ralph-init-hook-ordering-brainstorm.md`
- [x] #6 `tests/unit/pretools-hooks.bats` adds six new master-branch-guard test bodies — one per new exempt dir — each asserting a write under that dir on master returns exit 0 with no deny JSON
- [x] #7 Existing master-branch-guard exempt-case tests (.claude/, .gitignore, task branch, detached HEAD) continue to pass; existing deny-case test still produces the BLOCKED JSON
- [x] #8 Smoke verification: a simulated end-to-end /ralph-init against a scratch repo on master reaches Step 3.9 (.obsidian/* writes) without hook denial; invocation documented in task Implementation Notes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: Two-axis fix per design/ralph-init-hook-ordering-brainstorm.md addendum. (1) Widen master-branch-guard.sh exempt block with 6 editor/vault dirs (.obsidian/, .vscode/, .idea/, .cursor/, .zed/, .fleet/) + update header comment to enumerate them. (2) Mirror to skills/ralph-init/templates/claude/hooks/ for R11 parity. (3) Split SKILL.md Step 3.7a so .claude/settings.json move to new Step 3.11 after 3.10 (hook activation last). (4) Add 6 new positive exempt-case tests to tests/unit/pretools-hooks.bats (lines 121-156 section). (5) Run smoke verification of /ralph-init on scratch repo reaching Step 3.9 without denial.

Implementation:

AC #1, #2 — .claude/hooks/master-branch-guard.sh: header comment block (lines 2-3) now enumerates all 9 exempts (.claude/, design/, .obsidian/, .vscode/, .idea/, .cursor/, .zed/, .fleet/, .gitignore). Case statement (lines 30-38) gained 6 new exempt-case lines, each in both */<dir>/* and <dir>/* shapes matching existing .claude/ / design/ pattern.

AC #3 — skills/ralph-init/templates/claude/hooks/master-branch-guard.sh mirrored via cp. Verified R11 parity: 'diff .claude/hooks/master-branch-guard.sh skills/ralph-init/templates/claude/hooks/master-branch-guard.sh' produces no output.

AC #4 — SKILL.md Step 3.7a renamed to '.claude/hooks/ and .claude/settings.local.json (template write)'. .claude/settings.json write removed; added explanatory paragraph noting hook scripts remain dormant until Step 3.11 registers them.

AC #5 — SKILL.md gained Step 3.11 'hook activation — last act of init' immediately before Step 4, writing .claude/settings.json from templates/claude/settings.json. Body includes one-line rationale + back-pointer to design/ralph-init-hook-ordering-brainstorm.md.

AC #6 — tests/unit/pretools-hooks.bats gained 6 new positive-case tests, one per new exempt dir (.obsidian/, .vscode/, .idea/, .cursor/, .zed/, .fleet/), each asserting an Edit on master returns no deny JSON.

AC #7 — Full pretools-hooks.bats run: 31 tests, all pass. Existing exempt cases (.claude/, .gitignore), task-branch, detached-HEAD, and deny case all retained pass status.

AC #8 — Smoke verification: scratch git repo on master, hook copied in, then for each of the three Step 3.9 paths (.obsidian/app.json, .obsidian/hotkeys.json, .obsidian/snippets/wide-tables.css) piped a {tool_name:Edit, file_path:...} JSON into the hook. All three returned exit 0 with empty stdout (no deny JSON). Separate sanity check on master with README.md confirmed deny path still emits the BLOCKED JSON. Both axes (reorder + widen) each independently unblock the Step 3.9 case.

Invocation (reproducible):
  SMOKE_DIR=$(mktemp -d); SCRATCH="$SMOKE_DIR/scratch"
  git init -q -b master "$SCRATCH"
  git -C "$SCRATCH" config user.email t@t.t
  git -C "$SCRATCH" config user.name t
  git -C "$SCRATCH" commit -q --allow-empty -m init
  cp /workspace/.claude/hooks/master-branch-guard.sh "$SCRATCH/master-branch-guard.sh"
  for path in .obsidian/app.json .obsidian/hotkeys.json .obsidian/snippets/wide-tables.css; do
    out=$(cd "$SCRATCH" && echo "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$path\"}}" | bash master-branch-guard.sh 2>/dev/null)
    rc=$?
    [ -z "$out" ] && [ "$rc" = "0" ] && echo "PASS: $path" || echo "FAIL: $path"
  done

Result: 3 PASS / 0 FAIL.

Sibling task for Q4 upgrade-mode bug is filed per brainstorm addendum (separate task, not bundled here).

Commit: `62d362c` - task-139: Reorder ralph-init hook activation and widen master-branch-guard exempts

task-reviewer APPROVED. 8/8 AC verified, R10/R11/R12/R5 custom rules satisfied. 31/31 bats pass. Merging.
<!-- SECTION:NOTES:END -->
