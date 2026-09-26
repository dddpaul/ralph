---
id: TASK-239
title: >-
  Share the project .claude with the container instead of copying it into a
  volume
status: Done
assignee: []
created_date: '2026-09-26 08:31'
updated_date: '2026-09-26 11:28'
labels:
  - 'feature:ralph-init'
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

The devcontainer template mounts a named volume over `/workspace/.claude` and fills it once, in `postCreateCommand`, by copying from a read-only bind of the host's project `.claude`. Because `postCreateCommand` runs only at container creation, every later run works against a stale copy: host edits never reach the container, and the container's own commits carry its stale copy back into git — so a project's `.claude/skills/**` files silently revert after autonomous runs. On the source project this reverted the same skill file after nearly every Ralph run and was repaired by hand each time.

A second defect hides behind the first. `/workspace` presents as root-owned inside the container (that is how the file-sharing layer maps the workspace bind) while the container user is `node`, so git refuses the repository with `fatal: detected dubious ownership`. Nothing in the template or the Dockerfile sets `safe.directory`, and `node` has no `~/.gitconfig` — a long-lived container only works because someone set it by hand once. Recreating the container removes that, and the fresh container leaves Ralph without git at all: no `status`, no `commit`. The container user can write to both the worktree and `.git`; only the permission is missing.

Both defects ship in the template, so every project bootstrapped by `ralph-init` carries them. A survey of ~50 Ralph-enabled projects on the source machine found the whole-directory volume in all of them and the single-file overlay in none.

## Scope

In scope:
- Drop the whole-directory `.claude` volume and the `/workspace-host-claude` read-only bind from the devcontainer template.
- Bind a single container-specific settings file over `/workspace/.claude/settings.local.json`, and ship that file among the devcontainer templates. It carries only the sandbox switch — under `--dangerously-skip-permissions` the container needs no permission allowlist.
- Add an `initializeCommand` that seeds the host's `.claude/settings.local.json` when it is missing or empty. Without it, on a fresh clone Docker creates the bind destination as a 0-byte file the host's own Claude Code cannot parse.
- Replace the copying `postCreateCommand` with one that grants git `safe.directory` on the workspace folder.
- Update the `ralph-init` SKILL.md prose that describes the `.claude` overlay, and say there that changing mounts requires recreating the container.

Out of scope:
- The `.venv` volume and its `chown`. Its reason is the opposite one and still stands: a container-only interpreter path written into a host-bound `.venv` breaks the host virtualenv.
- Anything about `ralph.sh` or the orchestrator.
- Retrofitting existing projects. Each picks the fix up through the upgrade flow; note that upgrade mode U4 overwrites `.devcontainer/*`, so a project that already applied this fix by hand must not be surprised by it.
- Marking the single-file bind `readonly`. The source project weighed it and left the mount writable: a container-side write to a tracked file is cosmetic and visible in review, while a read-only mount would break every run if any startup path writes that file. Revisit only if such a write is observed.

## Files

- `plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json` (exists) — mounts, `postCreateCommand`, new `initializeCommand`.
- `plugins/ralph/skills/ralph-init/templates/devcontainer/container-settings.local.json` (to-create) — the one file that differs inside the container; sandbox off only.
- `plugins/ralph/skills/ralph-init/SKILL.md` (exists) — the prose describing the `.claude` overlay and the `.venv` volume alongside it.

## Verified reference implementation

The source project applied exactly this shape and verified it against live containers. The mount that replaces the volume:

```json
"source=${localWorkspaceFolder}/.devcontainer/container-settings.local.json,target=/workspace/.claude/settings.local.json,type=bind"
```

The file it points at:

```json
{
  "sandbox": {
    "enabled": false
  }
}
```

The two lifecycle hooks:

```json
"initializeCommand": "sh -c '[ -s .claude/settings.local.json ] || echo {} > .claude/settings.local.json'",
"postCreateCommand": "git config --global --add safe.directory /workspace",
```

Checked in a running container: the override wins over the user-level `sandbox.enabled: true` bind, the host keeps its sandbox enabled, `md5sum` of a `.claude/skills/**` file is identical inside and outside, a write from the container lands on the host file, and `git status` / `git log` work as `node` with no manual override. `initializeCommand` runs through `/bin/sh -c` with its working directory pinned to the workspace folder, so the relative path is safe and `${localWorkspaceFolder}` is unnecessary; `[ -s ]` makes it idempotent and it leaves a real host file alone.

## Source

Source: /Users/paul/Private/Alfa/Projects/enterprise@f39c1b95b219-dirty
Source tasks (read-only context, in that repo's backlog): TASK-62 (the overlay) and TASK-72 (the git permission). Both merged and reviewed there.

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
- [x] #1 The devcontainer template has no volume mount targeting the project .claude directory and no read-only bind of it — verified by grep over the template
- [x] #2 The template mounts one container-specific settings file over .claude/settings.local.json, and that file ships among the devcontainer templates
- [x] #3 The container settings file carries only the sandbox switch — no permission allowlist and no other keys
- [x] #4 An initializeCommand seeds the host .claude/settings.local.json when it is missing or empty, so Docker cannot leave an unparsable empty file in its place
- [x] #5 postCreateCommand grants git safe.directory on the workspace folder and no longer copies the .claude directory; the .venv volume chown is preserved
- [x] #6 The identical mount and lifecycle changes are mirrored into the live .devcontainer/devcontainer.json, so the exact-parity row for that pair in tests/unit/template-parity.bats still passes
- [x] #7 ralph-init SKILL.md describes the new scheme in BOTH Init (Step 3.x) and Upgrade Mode (U1-U5), and states that changing mounts requires recreating the container
- [x] #8 BOTH the template and the live devcontainer.json parse as JSON after stripping line-leading // comments
- [x] #9 uv run ruff check . is clean, uv run pytest passes, and LC_ALL=C bats tests/unit passes with no regressions in the pre-existing tests
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
AC rework before start (handoff acceptance gate): the original ACs scoped only the template, but tests/unit/template-parity.bats pins .devcontainer/devcontainer.json <-> templates/devcontainer/devcontainer.json as exact, so a template-only change breaks parity. Added an explicit live-mirror AC, widened the JSON-parse AC to both files, added LC_ALL=C bats tests/unit to the gate (the original gate was ruff+pytest only and structurally could not see the parity failure), and made the SKILL.md AC require BOTH Init and Upgrade Mode per project rule.

Plan: (1) template devcontainer.json — drop the claude-code-project-config volume and the /workspace-host-claude ro bind, add a single-file bind of .devcontainer/container-settings.local.json over /workspace/.claude/settings.local.json, add initializeCommand seeding the host file, rewrite postCreateCommand to keep only the .venv chown plus git safe.directory /workspace. (2) new template devcontainer/container-settings.local.json carrying only {"sandbox":{"enabled":false}}. (3) mirror both into live .devcontainer/ byte-identically. (4) register the new pair as an exact row in tests/unit/template-parity.bats and in the R11 table of .claude/task-reviewer-rules.md so the closure test stays satisfied. (5) ralph-init SKILL.md — new Init 3.6 note for the settings-file bind, repoint the .venv note cross-reference and the chown sentence, fix the mountinfo verification block, add the file to the U2 status table and U4 apply list, and state in U5 that mount changes need a container recreate. (6) README devcontainer section gets the same settings-file note. Gate: ruff, pytest, LC_ALL=C bats tests/unit, plus jq parse of both devcontainer.json after stripping line-leading // comments.

Commit: `a115cbf` - task-239: share the project .claude with the container instead of copying it into a volume

Commit: `6507a17` - task-239: list container-settings.local.json among the upgrade-checked files

Implemented: dropped the whole-directory .claude volume and the /workspace-host-claude ro bind; bind a single container-settings.local.json over .claude/settings.local.json (sandbox switch only); added an idempotent initializeCommand seeding the host file; postCreateCommand now grants git safe.directory /workspace and no longer copies .claude (the .venv chown is preserved, first). Mirrored to the live .devcontainer/ (exact parity pair), added the R11 parity row, and updated ralph-init SKILL.md in both Init and Upgrade Mode. New regression test tests/unit/devcontainer-claude-share.bats (mutation-checked: 8 of 11 fail against the pre-fix files). Review found one blocking defect: U2 'Files to check' never listed the new file, leaving the U3 row and U4 apply rule dangling, so an upgrading project would get the bind without its source and Docker would materialize a directory at the source path, breaking container creation. Fixed in 6507a17 by adding U2 item 16 and realigning the U3 table. Verdict APPROVED. Gates: ruff clean, pytest 498 passed, bats 123 ok with 3 failures (53/54/73) confirmed pre-existing on master 565997b.

Commit: `ba92648` - task-239: bump plugin version to 0.6.0 (minor)
<!-- SECTION:NOTES:END -->
