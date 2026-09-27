---
id: TASK-248
title: Stop the devcontainer image from freezing an old Claude Code version
status: Done
assignee: []
created_date: '2026-09-27 13:11'
updated_date: '2026-09-27 14:18'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

The devcontainer image installs Claude Code with a floating tag:

```dockerfile
ARG CLAUDE_CODE_VERSION=latest
...
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION} backlog.md
```

Because that `RUN` line never changes, Docker caches the layer permanently. `latest` is resolved **once**, at first build, and then frozen — every later build reuses the cached layer and the container's CLI silently ages forever. `devcontainer up --remove-existing-container` does not help: it recreates the *container* from the same cached *image*. Only `devcontainer build --no-cache` re-resolves the tag.

## Evidence (measured 2026-09-27)

| Where | Version |
|---|---|
| Devcontainer image | 2.1.259 |
| Host CLI | 2.1.267 |
| npm `latest` | 2.1.283 |

The container was 24 releases behind npm, and behind even the host. This is not cosmetic: it broke a real Ralph run. After TASK-243 set the default model to `claude-opus-5-5`, every iteration failed immediately with

```
API Error: 400 Claude Code 2.1.259 does not support this model; version 2.1.280 or newer is required.
```

so the loop exited after 12 seconds with 0 of 4 tasks done. A freshly-built image would have worked. The failure mode is nasty because the image looks current — it was "rebuilt" the same morning, reusing the cached npm layer.

## Direction

Make the installed CLI version an explicit, visible input rather than a silently frozen one. Two workable shapes, pick one and say why in the notes:

1. **Pin and bump** — set `CLAUDE_CODE_VERSION` to a concrete version in the devcontainer build args, so the value is in the diff, reviewable, and bumped deliberately. Cache invalidates whenever it changes.
2. **Cache-bust** — keep `latest` but force re-resolution, e.g. a build arg carrying a date or the npm-resolved version, so the layer cannot be reused silently.

Either way the requirement is the same: a rebuild must be able to pick up a newer CLI, and the version in use must be discoverable without exec'ing into a container.

## Parity

`.devcontainer/Dockerfile` is mirrored under `plugins/ralph/skills/ralph-init/templates/devcontainer/` (R11), so any change ships to every project through `ralph-init`. ralph-init SKILL.md must be updated in BOTH Init (Step 3.x) and Upgrade Mode (U1-U5).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The Claude Code version installed into the image is an explicit reviewable input, not a silently cached floating tag
- [x] #2 Changing that input invalidates the npm layer, so a rebuild demonstrably installs the newer CLI
- [x] #3 A documented command reports the CLI version an image will install without exec'ing into a running container
- [x] #4 The devcontainer README or SKILL.md notes say plainly that --remove-existing-container does NOT refresh the image, and name the command that does
- [x] #5 The change is mirrored into the ralph-init devcontainer templates and template-parity passes
- [x] #6 ralph-init SKILL.md documents it in both Init (Step 3.x) and Upgrade Mode (U1-U5)
- [x] #7 LC_ALL=C bats tests/unit and uv run pytest pass with no new failures
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: shape 1 (pin and bump). Pin CLAUDE_CODE_VERSION to a concrete semver in devcontainer.json build args (live + template); drop the Dockerfile ARG default and fail the build on empty/latest/next/non-semver, so the floating tag cannot come back silently; stamp the pin as an image LABEL and assert the installed CLI matches it. Document the lookup commands and that --remove-existing-container reuses the layer cache (devcontainer build --no-cache refreshes). Pytest guard over both copies. Why pin over cache-bust: the version lands in the diff and is reviewed; a date bust still hides which CLI you got and re-resolves latest non-reproducibly.

Commit: `f5ecaa8` - task-248: pin the devcontainer Claude Code version instead of a cached floating tag

Commit: `9717979` - task-248: require a strict X.Y.Z Claude Code pin and clarify the bump rebuild

Chose pin-and-bump over cache-bust: the version is in the diff and reviewed, and a bump invalidates the npm layer; a date bust would still re-resolve latest non-reproducibly and hide which CLI you got. Pinned CLAUDE_CODE_VERSION=2.1.283 (npm latest 2026-09-27) in both devcontainer.json copies; Dockerfile(.base) ARG has no default, the npm RUN rejects anything not strict X.Y.Z (grep -Eqx) and checks claude --version against the pin, LABEL dev.ralph.claude-code-version exposes it via docker image inspect. Upgrade mode: never downgrade a newer project pin; offer a confirm-only in-place Dockerfile patch. AC2 shown by cache-key structure + build-time version check + tests/python/test_devcontainer_claude_code_pin.py (guard run under sh) — Docker unavailable here, no real image build. Tests: pytest 598 passed; bats unit 110 with only #96 failing, identical on master (pre-existing). task-reviewer: APPROVED; its two optional notes (loose glob guard, bump wording) applied.

Commit: `d2e6c90` - task-248: bump plugin version to 0.6.6 (patch)
<!-- SECTION:NOTES:END -->
