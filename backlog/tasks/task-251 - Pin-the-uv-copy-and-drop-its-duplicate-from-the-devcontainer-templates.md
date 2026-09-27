---
id: TASK-251
title: Pin the uv copy and drop its duplicate from the devcontainer templates
status: Done
assignee: []
created_date: '2026-09-27 16:10'
updated_date: '2026-09-27 17:01'
labels:
  - 'feature:ralph-init'
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

`Dockerfile.base` and the `docs` / `python` install fragments each copy uv, so an assembled Documentation, Mixed or Python devcontainer carries the instruction **twice**, and all three copies pull the floating tag:

```
Dockerfile.base:98                COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
lang/Dockerfile.install.docs:4    COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
lang/Dockerfile.install.python:4  COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
```

The floating tag is the same failure mode the `CLAUDE_CODE_VERSION` pin exists to prevent, and `Dockerfile.base` argues against it in a comment two hunks above this very instruction: a tag is resolved once, at the first build, and the layer is then reused on every later build, so the image silently ages. The difference is that a stale Claude Code now fails loudly — the guarded npm step and the `claude --version` check make it visible — while a stale uv fails quietly. uv is what runs the orchestrator (`ralph.sh` ends in `exec uv run …`), what installs the interpreter (`uv python install 3.14`) and what every PEP 723 script in a downstream project is executed with, so an old uv shows up as a confusing resolver or interpreter-download error rather than as "your uv is from six months ago". Nothing in the image records which uv it carries, so neither `docker image inspect` nor a container probe can tell without running `uv --version`.

The duplicate copy is separately worth removing: the base already installs uv for every language, so the per-language copy adds a redundant layer and a second place a future pin has to be kept in step. A downstream Documentation project hit both while re-assembling its Dockerfile from the 0.7.0 templates — the duplication is what made the floating tag visible, because the same instruction appears twice with the same unpinned tag.

## Scope

In scope:
- Pin uv to a concrete version wherever the templates copy it, so bumping it changes the layer's cache key, in the same shape as the Claude Code pin (a build arg from `devcontainer.json`, or a literal, as long as a bump is a diff).
- Remove the redundant copy: keep one, in the base, since it applies to every language.
- Record what the image carries the way the Claude Code pin does, so the version is readable without starting a container.
- A test that rejects a floating tag in any uv copy in the templates, so this cannot come back.

Out of scope:
- The Claude Code pin itself — already done.
- The stale language-runtime copy — already done (TASK-242).
- Anything in the downstream project's own repository.

## Files

- `plugins/ralph/skills/ralph-init/templates/devcontainer/Dockerfile.base` (exists) — the uv + Python 3.14 block, line 98
- `plugins/ralph/skills/ralph-init/templates/devcontainer/lang/Dockerfile.install.docs` (exists) — the redundant copy, line 4
- `plugins/ralph/skills/ralph-init/templates/devcontainer/lang/Dockerfile.install.python` (exists) — the redundant copy, line 4
- `plugins/ralph/skills/ralph-init/templates/devcontainer/devcontainer.json` (exists) — where a build arg for the pin would live, next to `CLAUDE_CODE_VERSION`
- `tests/python/test_devcontainer_claude_code_pin.py` (exists) — the pattern to follow: it is the pin test for the other floating tag
- `tests/python/test_devcontainer_python_runtime.py` (exists) — the fragment-level guard added by TASK-242

## Source

Source: /Users/paul/Private/Alfa/Projects/enterprise@2dc0e07c2290

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
- [x] #1 The templates copy uv exactly once for every language flavour — an assembled docs, python, node and go Dockerfile each carry one uv copy
- [x] #2 Every uv copy in the templates pins a concrete version, and bumping that version changes the layer's cache key so the next build reinstalls
- [x] #3 A test rejects a floating tag in any uv copy in the templates, in the same shape as the Claude Code pin test
- [x] #4 The version the image carries is readable without starting a container, as the Claude Code pin already is
- [x] #5 uv --version inside a freshly built devcontainer reports the pinned version
- [x] #6 The build still completes and uv python install 3.14 still succeeds, and uv run works inside the container
- [x] #7 uv run pytest passes and uv run ruff check . passes; shell edits satisfy the R5 GNU/BSD portability rule
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: pin uv via a UV_VERSION build arg in both devcontainer.json copies, mirroring the CLAUDE_CODE_VERSION shape. Key constraint found by testing, not assumption: 'COPY --from' cannot expand a build arg — Docker fails with 'variable expansion is not supported for --from, define a new stage with FROM using ARG from global scope as a workaround'. So uv arrives via a named stage: a global 'ARG UV_VERSION' before the first FROM (needed because lang.go declares its own FROM), then 'FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv-bin', and 'COPY --from=uv-bin /uv /usr/local/bin/uv' in the devcontainer stage. Guard RUN rejects non-X.Y.Z and asserts 'uv --version' matches the pin, then keeps 'uv python install 3.14' in the same layer. LABEL dev.ralph.uv-version makes it readable via docker image inspect (AC4). Drop the duplicate COPY from lang/Dockerfile.install.docs and .install.python — the base copies uv for every flavour, so node/go (which carry 0 copies today) and docs/python all end at exactly one. Both the template Dockerfile.base and the live .devcontainer/Dockerfile change, because tests/python/test_devcontainer_claude_code_pin.py parametrizes over both and the new uv test mirrors it. Checked 250's stale-runtime-copy.sh will not flag the uv copy: its guarded() tests the COPY source path (/uv), not the destination, so only /usr/local-rooted sources qualify — will re-verify after the edit. Pin 0.12.19 (current PyPI latest; local host uv is 0.12.15). AC5/AC6 need a real image build, which I run on the host since the devcontainer has no docker socket.

Commit: `8f66a2c` - task-251: pin the uv copy and drop its duplicate from the devcontainer templates

Host-side invocation evidence (R17). The devcontainer has no docker socket, so every build below ran on the host.

AC1 - one uv copy per flavour: the only uv references left in the templates are 'FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv-bin' and one 'COPY --from=uv-bin /uv /usr/local/bin/uv', both in Dockerfile.base. All four install fragments (docs, python, node, go) now contain zero.
AC2 - a bump really changes what is installed: built twice from the same Dockerfile, changing only the build arg. UV_VERSION=0.12.19 produced an image reporting 'uv 0.12.19'; UV_VERSION=0.12.15 produced 'uv 0.12.15'. The pin flows through the stage image, so the layer cache key follows it.
AC3 - tests/python/test_devcontainer_uv_pin.py (23 tests) mirrors the Claude Code pin test: semver build arg in both devcontainer.json copies, one pinned stage, one COPY from that stage, no direct 'COPY --from=ghcr.io/astral-sh/uv:' (it cannot be pinned - see below), the LABEL, the guard run for real under sh over 7 values, no second copy in any fragment, and a mutated-Dockerfile check so none of it is vacuous.
AC4 - readable without starting a container: 'docker image inspect --format {{index .Config.Labels "dev.ralph.uv-version"}}' returns 0.12.19.
AC5 - 'uv --version' in the built image reports 'uv 0.12.19 (aarch64-unknown-linux-musl)'.
AC6 - build completes; 'uv python list' shows 3.14 present; 'uv run --no-project' executes a script successfully. Also verified through 'devcontainer build' with no manual --build-arg, so the devcontainer.json wiring works: labels came out uv 0.12.19 / claude 2.1.283.
Guard negative case: UV_VERSION=latest FAILS the build with "UV_VERSION must be a concrete X.Y.Z, got 'latest'". Note ghcr.io/astral-sh/uv:latest is a real image, so the FROM succeeds and only the guard stops it - the guard does real work.
No regression in TASK-250: 'stale-runtime-copy.sh check .devcontainer/Dockerfile' still exits 0. Its guarded() tests the COPY source path ('/uv'), not the destination, so the uv copy is correctly not flagged.

Two findings worth recording. (1) 'COPY --from' cannot expand a build arg - Docker fails with 'variable expansion is not supported for --from, define a new stage with FROM using ARG from global scope as a workaround'. That is why uv arrives via a named stage and why a global ARG sits before the first FROM (lang.go declares its own FROM, so it cannot go later). (2) Dockerfile.install.python must NOT end with a trailing newline: the '{{LANGUAGE_INSTALL}}' substitution then yields one blank line rather than two, and adding one broke three TASK-250 patcher tests. Convention restored and left unchanged for node/go, which share it.

Review follow-up (task-reviewer, CHANGES REQUESTED -> fixed). Blocking finding: the pin was delivered to existing projects as a no-op. U4 rewrites devcontainer.json so an upgraded project gains "UV_VERSION", but U2 item 12 always skips .devcontainer/Dockerfile — which still holds the literal 'COPY --from=ghcr.io/astral-sh/uv:latest' and no ARG UV_VERSION. Docker then reports the arg unused, uv stays frozen on latest, and no dev.ralph.uv-version label appears: the project looks pinned to a grep while the defect is intact, a false signal this change would have introduced. The asymmetry the reviewer identified is the crux — for CLAUDE_CODE_VERSION a pre-existing 'ARG ...=latest' absorbs the build arg, so that Dockerfile patch is hardening; for uv 'COPY --from' takes a literal and cannot expand an arg, so the patch is REQUIRED for the pin to do anything. Fixed by adding three prose sections, no code: ralph-init SKILL.md Init gets a 'uv version pin' note (mechanism, why the ARG is global, the no-default/InvalidDefaultArgInFrom trade, bump procedure, both read-back commands, and the plain-docker-build caveat); ralph-init SKILL.md Upgrade Mode gets a 'uv version pin on upgrade' note that deliberately does NOT reuse the Claude Code note's 'fixed by devcontainer.json alone' wording, states the patch is required, offers it confirm-only with the diff and prompt, labels it 'skipped (assembled; uv pin patched)' in U5, and requires the summary to say the pin is inert when the user declines; README.md gets a 'uv version is pinned' paragraph including the 'invalid reference format' failure of a plain docker build. This also satisfies the standing convention that ralph-init changes land in BOTH Init (Step 3.x) and Upgrade Mode (U1-U5), since existing projects only receive changes through 'ralph-init upgrade'.
Also applied two non-blocking notes: reworded the comment in test_devcontainer_python_runtime.py that this change invalidated (the uv line there is now kept deliberately as the pre-251 shape the guard must still ignore, since no fragment carries uv any more), and added an assertion that the global ARG precedes the first FROM — the test explained that invariant without pinning it. Left the 'uv --version | grep -qF' substring match as-is: the reviewer did not require it and it is the identical shape to the shipped 'claude --version' check, so tightening only one of the two would introduce an inconsistency; worth a follow-up covering both if wanted. Gates after the fixes: uv run pytest 642 passed 1 skipped, uv run ruff check . clean, LC_ALL=C bats tests/unit 110 with only the two pre-existing macOS APFS failures (#34/#35), bats tests/integration 0 failures.

Commit: `0e6dfdc` - task-251: document the uv pin in ralph-init Init, Upgrade Mode and the README

Commit: `74d93e2` - task-251: resolve the upgrade-note cross-references and cover a third patch label

Re-review 2 (task-reviewer): APPROVED, with two fold-ins landed before merge. (1) Restoring the dropped noun had pushed the test comment to 103 characters; re-wrapped to the reviewer's exact six lines, longest line now 86. The reviewer also explained why the gate missed it: pyproject.toml sets line-length = 88 but extend-select = ["I","B","UP","SIM"] omits E501, which is not in ruff's defaults either, so 'ruff check' honours the value only through 'ruff format'. Confirmed repo-wide: 26 over-limit lines across 12+ files, and 'ruff format --check' reports 36 of 76 files would be reformatted. Pre-existing and out of scope here — filed as TASK-253. While measuring it I found my own new test file was among the 36, so I ran 'ruff format' on that one file only (a single string-concat wrap, no semantic change); it is now format-clean at 88. (2) Pluralised SKILL.md:763 with the reviewer's minimal edit — 'When either version-pin patch also fired, join the outcomes in one label' — which keeps the declined-label join that line uniquely carries and that line 748 does not. Gates after the fold-ins: uv run pytest 642 passed 1 skipped, uv run ruff check . clean, ruff format --check clean on both files I touched, LC_ALL=C bats tests/unit 110 with only the two pre-existing macOS APFS failures. Also filed TASK-252 from the reviewer's recommended follow-up: the uv patch offer is conditioned on devcontainer.json being outdated, so a declined patch is never re-offered and a later run reports everything up to date on an unpinned project.

Commit: `92da33a` - task-251: rewrap the runtime-guard comment and pluralise the pin-patch reference

Done: uv pinned to 0.12.19 via a UV_VERSION build arg in both devcontainer.json copies, pulled through a 'FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv-bin' stage (COPY --from cannot expand a build arg) and copied once in Dockerfile.base for every language; the duplicate copies are gone from the docs and python install fragments, so all four flavours carry exactly one. Guarded RUN rejects a non-X.Y.Z value and checks 'uv --version' against the pin; LABEL dev.ralph.uv-version makes it readable via docker image inspect. Init and Upgrade Mode notes plus a README paragraph make the pin reach existing projects, with the Upgrade note stating that the Dockerfile patch is required rather than optional because nothing absorbs the build arg. New tests/python/test_devcontainer_uv_pin.py (23 tests) mirrors the Claude Code pin test across both copies; the TASK-242 fragment guard was relocated to assert the base carries uv and the fragments do not. Verified on the host by real builds at two pins, a rejected floating tag, and a devcontainer build with no manual --build-arg. 7/7 ACs, task-reviewer APPROVED after two rework rounds.

Commit: `0256a3d` - task-251: bump plugin version to 0.7.1 (patch)
<!-- SECTION:NOTES:END -->
