---
id: TASK-272
title: >-
  Declare CLAUDE_CODE_VERSION next to the npm step so a version bump rebuilds
  only the image tail
status: Done
assignee: []
created_date: '2026-10-05 17:21'
updated_date: '2026-10-05 18:12'
labels:
  - 'feature:ralph-init'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

The version pin was meant to rebuild only the Claude Code layer when `CLAUDE_CODE_VERSION` is bumped — the template says so at the npm step ("Bumping CLAUDE_CODE_VERSION changes this layer's cache key, so the next build reinstalls"). It rebuilds the whole image instead, because `ARG CLAUDE_CODE_VERSION` is declared at the top of the final stage (`Dockerfile.base` line 31), before every `RUN`. Docker's documented rule: when an `ARG` value differs from the previous build, every `RUN` after the `ARG` declaration misses the cache, since each `RUN` sees the argument implicitly as an environment variable — not just the instructions that reference it.

Measured downstream (stacks, 2026-10-05): after the upgrade moved the pin from `latest` to `2.1.283`, `docker buildx history inspect` showed the build missing the cache from step 2 of 17 (the first `apt-get install`: JRE, graphviz, plantuml, fonts), so the whole 4.6 GB documentation image is being rebuilt. On a colima VM with ~100 KB/s to the Debian mirror that is about an hour per Claude Code bump. Before the pin, builds of that image took ~3 s because the value stayed `latest`.

## Scope

In scope:
- Declare `ARG CLAUDE_CODE_VERSION` immediately before `LABEL dev.ralph.claude-code-version` (the `# ---- Claude ----` block), and drop the early declaration together with its comment block (move the comment, keeping the "no default on purpose" rationale).
- Fix the npm-step comment so it states the real effect: a bump re-runs this step and everything after it, nothing before it.
- Mirror the move in the live `.devcontainer/Dockerfile` (template parity).
- Extend the pin test so a `RUN` between the `ARG` and the guarded npm `RUN` fails it.
- Update the Upgrade Mode text that tells ralph-init how to patch an existing project's Dockerfile for the version pin, so the patched `ARG` lands next to the npm step, not at the top.

`UV_VERSION` already follows the right pattern (global `ARG` before the first `FROM`, re-declared right before its `LABEL`); use it as the model. Before moving, confirm with `grep -n CLAUDE_CODE_VERSION` that nothing between the old and new positions references the argument.

Out of scope:
- Detecting or patching the early `ARG` in already-assembled project Dockerfiles at upgrade time (U2 skips them as assembled) — record a proposed follow-up in the notes, modelled on `floating-uv-copy.sh`.
- Changing the pinned version value, other build args, or the image contents.

## Files

- `plugins/ralph/skills/ralph-init/templates/devcontainer/Dockerfile.base` (exists) — `ARG CLAUDE_CODE_VERSION` at line 31, the `# ---- Claude ----` block with `LABEL` at line 106
- `.devcontainer/Dockerfile` (exists) — same pair at lines 37 and 121 (template parity)
- `tests/python/test_devcontainer_claude_code_pin.py` (exists) — pins the default-less `ARG`; add the placement check
- `tests/unit/template-parity.bats` (exists) — must keep passing
- `plugins/ralph/skills/ralph-init/SKILL.md` (exists) — Upgrade Mode "Claude Code version pin on upgrade", step 2 ("Patch the Dockerfile in place")

## Source

Source: /Users/paul/Private/Alfa/Projects/standard/stacks@bf209f77170a
Source reference (read-only context, do NOT modify): /Users/paul/Private/Alfa/Projects/standard/stacks/.devcontainer/Dockerfile (`ARG CLAUDE_CODE_VERSION` at line 39, assembled from the current template).

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, build command, or visible behavior — not "works correctly").
3. All dependencies in the task's frontmatter are status=Done.
4. Out-of-scope items are not accidentally pulled in by ambiguous AC.

The cache-behaviour AC needs a host with Docker: a Ralph run inside the devcontainer cannot build images. TASK-271 also edits `Dockerfile.base` (the sudoers line near the end); the two changes touch different lines.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 In Dockerfile.base and .devcontainer/Dockerfile, ARG CLAUDE_CODE_VERSION appears exactly once in the final stage, and no RUN instruction lies between it and the guarded npm RUN
- [x] #2 The npm-step comment in Dockerfile.base no longer claims the bump changes only this layer's cache key; it states that the bump re-runs this step and those after it
- [x] #3 tests/python/test_devcontainer_claude_code_pin.py fails on a Dockerfile with a RUN between the ARG and the npm RUN, passes on the moved template, and tests/unit/template-parity.bats passes
- [x] #4 The SKILL.md Upgrade Mode step that patches an existing Dockerfile for the version pin places the ARG immediately before the LABEL dev.ralph.claude-code-version line
- [x] #5 On a host with Docker, the node-flavour Dockerfile assembled from the template is built twice with two different concrete CLAUDE_CODE_VERSION values; the second build log shows every step before the LABEL/npm step as CACHED, and the log excerpt is recorded in the task notes
- [x] #6 uv run pytest and uv run ruff check . pass
- [x] #7 A proposed follow-up for upgrade-time detection of the early ARG in already-assembled project Dockerfiles is recorded in the task notes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Commit: `95b016e` - task-272: declare CLAUDE_CODE_VERSION right before the npm step so a bump rebuilds only the image tail

Plan: handoff checklist yellow — all (exists) paths present, no deps, AC #5 needs a Docker host (no docker binary in this container), deferred to the host as in TASK-271. grep -n CLAUDE_CODE_VERSION confirmed nothing between the old ARG (top of final stage) and the LABEL references it, and the {{LANGUAGE_*}} fragments do not reference it. Move the ARG + its rationale comment into the '# ---- Claude ----' block right before the LABEL in Dockerfile.base and .devcontainer/Dockerfile; rewrite the npm-step comment (bump re-runs this step and those after it, nothing before it); add placement_problems() to the pin test (ARG once in the final stage, before the npm RUN, no RUN between) with mutation tests; update SKILL.md Init pin note + Upgrade Mode step 2 and the README pin paragraph.

Verification: the new check flags master's Dockerfile.base ('RUN between the ARG and the npm RUN …: [RUN apt-get update …]') and passes both moved copies. Gates: uv run ruff check . clean; uv run pytest 822 passed, 3 skipped; LC_ALL=C bats tests/unit/template-parity.bats 12/12 ok; bats tests/unit 153 ok, 1 not ok (#140 settings.local.json shape — the known pre-existing failure caused by the untracked local file, unrelated).

Proposed follow-up task (AC #7, not created here): 'Detect and patch the early CLAUDE_CODE_VERSION ARG in assembled devcontainer Dockerfiles on upgrade'. Add plugins/ralph/skills/ralph-init/scripts/early-claude-arg.sh, modelled on floating-uv-copy.sh: 'check' parses .devcontainer/Dockerfile (joined continuations, comments dropped), takes the final stage, and reports 'early claude-code arg' when a RUN lies between ARG CLAUDE_CODE_VERSION and the npm @anthropic-ai/claude-code@ RUN; 'patch' prints the file with that ARG line (and its 'No default on purpose' comment paragraph) removed and re-inserted immediately before LABEL dev.ralph.claude-code-version (or before the npm RUN when the LABEL is absent), exit 3 when the ARG has a default other than none / appears twice / the npm RUN is missing. U2 adds 'early claude-code arg' to the Dockerfile status; Upgrade Mode offers the patch confirm-only, labelled 'skipped (assembled; claude arg moved)', joined after 'version pin patched'. A pytest with fixture Dockerfiles pins it: early flagged and patched, moved no-op, unparseable reported without patch.

task-reviewer (ralph:task-reviewer, installed 0.12.0): APPROVED, SCORE 10, 0 blocking, 0 minor.

Not marked Done and not merged: AC #5 is unchecked until a Docker host proves the cache behaviour. Host steps: assemble the node-flavour Dockerfile from the template (or use .devcontainer/Dockerfile), then run 'docker buildx build --progress=plain --build-arg CLAUDE_CODE_VERSION=2.1.283 --build-arg UV_VERSION=<pin> --build-arg TZ=UTC -f <Dockerfile> .devcontainer' and again with a different concrete CLAUDE_CODE_VERSION (e.g. 2.1.282); in the second log every step before the LABEL/npm step must show CACHED. Paste the excerpt here, check AC #5, then Done + Merge step 6 (bump-version.sh --auto bumps the plugin version, since Dockerfile.base and ralph-init SKILL.md changed).

AC #5 host verification (macOS, Docker buildx): assembled the node flavour from the task-272 template exactly as ralph-init does (Dockerfile.base with {{LANGUAGE_STAGE}}/{{LANGUAGE_INSTALL}} replaced by lang/Dockerfile.lang.node and lang/Dockerfile.install.node; context = that Dockerfile + init-firewall.sh). Build 1: docker buildx build --progress=plain --build-arg CLAUDE_CODE_VERSION=2.1.283 --build-arg UV_VERSION=0.12.19 --build-arg TZ=UTC — exit 0, every step 2/12-12/12 ran. Build 2, same command with CLAUDE_CODE_VERSION=2.1.284 — exit 0, image label dev.ralph.claude-code-version=2.1.284. Build 2 log excerpt: '#8 [stage-1  2/12] RUN apt-get update && apt-get install ... #8 CACHED' / '#11 [stage-1  3/12] RUN mkdir -p /usr/local/share/npm-global ... #11 CACHED' / '#9 [stage-1  4/12] RUN SNIPPET=... #9 CACHED' / '#12 [stage-1  5/12] RUN mkdir -p /workspace /home/node/.claude ... #12 CACHED' / '#10 [stage-1  6/12] WORKDIR /workspace #10 CACHED' / '#13 [stage-1  7/12] RUN sh -c "$(wget -O- .../zsh-in-docker.sh)" ... #13 CACHED' / '#14 [stage-1  8/12] RUN { echo "2.1.284" | grep -Eqx ... npm install -g @anthropic-ai/claude-code@2.1.284 ... DONE 23.9s', then 9/12-12/12 re-ran (COPY uv 0.9s, uv python install 7.4s, COPY firewall 0.1s, sudoers 0.2s). Step 1/12 (FROM node:20@sha256:8f693e...) printed 'resolve ... 0.2s done / DONE 0.3s' in build 2 (it printed CACHED in build 1): a digest resolve of the local base image with no layer pull — not a build step, nothing rebuilt. So a bump re-runs the npm step and those after it, nothing before it. Placement check on the host: master's Dockerfile.base -> 'RUN between the ARG and the npm RUN rebuilds on every bump: [RUN apt-get update ...]'; task-272 Dockerfile.base and the assembled node file -> OK. Host gates: uv run ruff check . clean; uv run pytest 823 passed, 2 skipped (pin test 22 passed); LC_ALL=C node_modules/.bin/bats tests/unit 154 ok, 0 not ok.

Commit: `52554f2` - task-272: bump plugin version to 0.13.3 (patch)
<!-- SECTION:NOTES:END -->
