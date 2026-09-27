---
id: TASK-252
title: Re-offer a declined Dockerfile pin patch on later upgrade runs
status: To Do
assignee: []
created_date: '2026-09-27 16:55'
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
- [ ] #1 U2 gives .devcontainer/Dockerfile a status reflecting a floating uv copy, set independently of whether devcontainer.json is outdated
- [ ] #2 U3 treats that status as pending work, so the All-Ralph-files-are-up-to-date shortcut does not fire while the Dockerfile is unpinned
- [ ] #3 U4 offers the uv patch off the U2 status rather than off having rewritten devcontainer.json, so a previously declined patch is offered again
- [ ] #4 A second upgrade run on a project that declined the patch re-offers it, and the run does not report everything up to date
- [ ] #5 A project whose Dockerfile already carries the pinned uv stage gets the plain skipped (assembled) status and no offer
- [ ] #6 The new status and its U5 label compose with the stale-runtime and Claude Code pin labels when more than one applies
- [ ] #7 A test covers both branches: a floating uv copy is detected, and a correctly pinned Dockerfile is not flagged
- [ ] #8 LC_ALL=C bats tests/unit, uv run pytest and uv run ruff check . all pass with no new failures
<!-- AC:END -->
