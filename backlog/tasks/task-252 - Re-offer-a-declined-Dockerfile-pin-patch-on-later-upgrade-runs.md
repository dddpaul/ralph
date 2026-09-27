---
id: TASK-252
title: Re-offer a declined Dockerfile pin patch on later upgrade runs
status: Done
assignee: []
created_date: '2026-09-27 16:55'
updated_date: '2026-09-27 17:49'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

The uv pin patch offered in Upgrade Mode can only fire while `.devcontainer/devcontainer.json` is **outdated**. Its trigger is "whenever U4 adds or changes `UV_VERSION`", and U4 only rewrites files U2 marked outdated. So a user who declines the Dockerfile patch once never sees it again: on the next upgrade run `devcontainer.json` is already current, U4 does not touch it, the offer cannot fire, and U3 prints

```
All Ralph files are up to date.
```

while the project is not pinned at all — `UV_VERSION` sits in `devcontainer.json`, the Dockerfile still has the literal `COPY --from=ghcr.io/astral-sh/uv:latest`, Docker reports the arg unused, and no `dev.ralph.uv-version` label exists. That is the same false-confidence state TASK-251 set out to remove, reached through a decline instead of through never being offered.

Narrow today, permanent later: every existing project's `devcontainer.json` is outdated right now, so the offer does fire on the upgrade that matters, and the U5 rule tells a declining user plainly that the pin is inert. The hole only opens on the second run.

## Direction — the shape TASK-250 already uses

Make the Dockerfile's own state a first-class U2 status, independent of `devcontainer.json`, exactly as the stale-runtime check does:

- **U2 item 12** (`plugins/ralph/skills/ralph-init/SKILL.md`, the `.devcontainer/Dockerfile` row) already runs `stale-runtime-copy.sh check` and, on exit 1, sets **skipped (assembled; stale runtime copy)** regardless of any other file's status. Add a second, independent condition for a uv copy on a floating tag — for example a `check` mode that reports a `COPY --from=ghcr.io/astral-sh/uv:<non-pinned>` with no `ARG UV_VERSION` in the file — and give it its own status suffix.
- **U3** already carves the stale-runtime case out of the "All Ralph files are up to date." shortcut and treats it as pending work. Extend that carve-out to the new status so the offer is reachable on any run.
- **U4** then offers the existing uv patch off the U2 status rather than off "U4 changed devcontainer.json".

Both conditions can hold at once, so the statuses and U5 labels must compose, as the existing `; `-joined labels do.

## Out of scope

- The uv pin itself, the fragment de-duplication, and the Init/Upgrade/README prose — all done in TASK-251.
- The stale language-runtime copy — done in TASK-250.
- Tightening `uv --version | grep -qF` to a non-substring match: a separate concern that should cover the identical `claude --version` check at the same time, or neither.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 U2 gives .devcontainer/Dockerfile a status reflecting a floating uv copy, set independently of whether devcontainer.json is outdated
- [x] #2 U3 treats that status as pending work, so the All-Ralph-files-are-up-to-date shortcut does not fire while the Dockerfile is unpinned
- [x] #3 U4 offers the uv patch off the U2 status rather than off having rewritten devcontainer.json, so a previously declined patch is offered again
- [x] #4 A second upgrade run on a project that declined the patch re-offers it, and the run does not report everything up to date
- [x] #5 A project whose Dockerfile already carries the pinned uv stage gets the plain skipped (assembled) status and no offer
- [x] #6 The new status and its U5 label compose with the stale-runtime and Claude Code pin labels when more than one applies
- [x] #7 A test covers both branches: a floating uv copy is detected, and a correctly pinned Dockerfile is not flagged
- [x] #8 LC_ALL=C bats tests/unit, uv run pytest and uv run ruff check . all pass with no new failures
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: new scripts/floating-uv-copy.sh check (Dockerfile-only, stage-aware); U2 item 12 derives 'floating uv copy' independently of devcontainer.json, joined uv-first with 'stale runtime copy'; U3 carve-out extended; U4 uv offer keyed to the U2 status (guarded on devcontainer.json carrying UV_VERSION); U5 labels; tests in tests/python/test_upgrade_floating_uv_copy.py.

Commit: `243b5a5` - task-252: re-offer the uv pin patch off a Dockerfile-derived U2 status

Done: floating-uv-copy.sh check drives U2 'floating uv copy'; U3/U4/U5 key off it, so a declined uv patch is re-offered on every later run. U4 skips the offer (label 'needs devcontainer.json') when devcontainer.json lacks UV_VERSION. Gates: pytest 669 passed, ruff clean, bats 109/110 (#96 pre-existing on master). task-reviewer APPROVED. Non-blocking reviewer notes left open: FROM --platform stage lines and case-insensitive stage names are not parsed; suffixed tags like 0.8.22-alpine are flagged; U2 item 12 does not say what to do on exit 2 (same as the stale-runtime check).

Commit: `d712ca0` - task-252: bump plugin version to 0.8.0 (minor)
<!-- SECTION:NOTES:END -->
