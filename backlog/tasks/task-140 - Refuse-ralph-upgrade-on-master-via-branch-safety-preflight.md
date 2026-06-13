---
id: TASK-140
title: Refuse ralph upgrade on master via branch-safety preflight
status: In Progress
assignee: []
created_date: '2026-06-13 19:17'
updated_date: '2026-06-13 19:20'
labels:
  - 'feature:ralph-init-hook-ordering'
dependencies:
  - TASK-139
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Upgrade-mode (U4 in `skills/ralph-init/SKILL.md`) overwrites root-level files — ralph.sh, CLAUDE.md, .git/hooks/*, .devcontainer/* — all paths that master-branch-guard denies on master. If a user runs ralph upgrade on master with hooks already installed, every U4 write is blocked. Has not surfaced because upgrades typically happen from a task branch (project convention), but it is latent and will trip the first user who tries it from master.

Brainstorm Q4 lock (2026-06-13): add a U1.5-shaped preflight that refuses ralph upgrade on master unless on a task branch. Sibling to TASK-139 with --dep, same feature family. Keeps the TASK-139 PR small and the upgrade-mode fix has been latent forever, so no urgency.

Approach: insert a "Branch Safety" step in the upgrade-mode flow before any file reads. Refuse on master (and detached HEAD) with a clear, recoverable message naming the next command.

Design conclusions: `design/ralph-init-hook-ordering-brainstorm.md` (Q4 lock, addendum 2026-06-13).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `skills/ralph-init/SKILL.md` adds a new "U1.5: Branch Safety" step placed between U1 (Preflight) and the existing Legacy File Migration step (which gets renumbered to U1.6); section header text and any internal cross-references updated accordingly
- [x] #2 The new step runs `git rev-parse --abbrev-ref HEAD` and refuses to proceed when output is "master" or "HEAD" (detached); refusal fires before any file reads in U2 onward (no side effects on refusal)
- [x] #3 Refusal message includes a concrete recovery command (e.g., git checkout -b task-NNN-ralph-upgrade master) and instructs the user to re-invoke upgrade afterward
- [x] #4 On non-master, non-detached branches, upgrade-mode behavior is unchanged from existing U1.6 (formerly U1.5) onward — no regression in the proceed path
- [x] #5 Smoke verification documented in task Implementation Notes: invoking upgrade-mode on master surfaces the refusal message verbatim; invoking on a task branch passes the new preflight without printing the refusal
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: extend skills/ralph-init/SKILL.md upgrade-mode flow with a new 'U1.5: Branch Safety' step inserted between U1 and the existing Legacy File Migration (renumbered to U1.6). The new step runs git rev-parse --abbrev-ref HEAD and refuses on master or HEAD (detached) with a concrete recovery command. No file reads on refusal. Smoke verify both paths (refuse on master / proceed on task branch).

Commit: `c4a366a` - init

Implementation:

AC #1 — skills/ralph-init/SKILL.md: inserted new section '### U1.5: Branch Safety' between U1 (Preflight, line 379) and the existing legacy-migration section. Renamed the existing 'U1.5: Legacy File Migration' to '### U1.6: Legacy File Migration'. Section order now: U1 → U1.5 (Branch Safety) → U1.6 (Legacy Migration) → U2 → U3 → U4 → U5. No internal cross-references to U1.5 elsewhere in the file (verified via grep), so no further edits needed.

AC #2, #4 — Branch detection: U1.5 runs 'git rev-parse --abbrev-ref HEAD' and refuses when output is 'master' or 'HEAD' (the latter is git's marker for detached HEAD). Refusal explicitly stops the flow before any file reads (no Glob, no Read calls). On any other branch, proceeds silently to U1.6.

AC #3 — Refusal message: includes the verbatim recovery command 'git checkout -b task-<id>-ralph-upgrade master' and instructs the user to re-invoke upgrade after switching branches. Also includes a back-pointer to design/ralph-init-hook-ordering-brainstorm.md (Q4) for rationale.

AC #5 — Smoke verification: ran the branch-detection logic in a scratch repo on master, task-99-foo, and detached-HEAD setups. All three matched expected behavior:

  setup=master       branch=master         verdict=REFUSE
  setup=task-99-foo  branch=task-99-foo    verdict=PROCEED to U1.6
  setup=detached     branch=HEAD           verdict=REFUSE

Reproducible invocation:

  SMOKE=$(mktemp -d -p tmp)
  git init -q -b master "$SMOKE"
  git -C "$SMOKE" -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
  for setup in master task-99-foo detached; do
    case "$setup" in
      master)    git -C "$SMOKE" checkout -q master ;;
      task-*)    git -C "$SMOKE" checkout -q -B task-99-foo ;;
      detached)  git -C "$SMOKE" checkout -q --detach HEAD ;;
    esac
    branch=$(git -C "$SMOKE" rev-parse --abbrev-ref HEAD)
    [ "$branch" = master ] || [ "$branch" = HEAD ] && v=REFUSE || v='PROCEED to U1.6'
    echo "setup=$setup branch=$branch verdict=$v"
  done

Regression check: tests/unit/pretools-hooks.bats — 31/31 pass. No R11 hook files touched in this task; parity intact (verified via diff).
<!-- SECTION:NOTES:END -->
