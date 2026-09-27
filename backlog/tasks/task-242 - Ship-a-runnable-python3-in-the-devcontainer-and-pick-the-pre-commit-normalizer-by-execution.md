---
id: TASK-242
title: >-
  Ship a runnable python3 in the devcontainer and pick the pre-commit normalizer
  by execution
status: Done
assignee: []
created_date: '2026-09-27 06:36'
updated_date: '2026-09-27 08:08'
labels:
  - 'feature:ralph-init'
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

The devcontainer image the templates build ships a `python3` that cannot start, and the `pre-commit` template then picks exactly that interpreter — so **every commit made inside a devcontainer is rejected** for Documentation, Mixed and Python projects. An autonomous Ralph run in a container cannot close a single task: it implements, then dies at the commit.

Two template defects compose into it.

First, the image. `Dockerfile.base` is `FROM node:20` — Debian bookworm, glibc 2.36. The language fragments add `FROM python:3.14 AS python-runtime` and `COPY --from=python-runtime /usr/local /usr/local`; the official `python:3.14` image is built on a newer Debian, so what lands in the image is an interpreter linked against a glibc the image does not have, installed first in `PATH`:

```
/usr/local/bin/python3 -> python3.14          (copied stage, root-owned)
python3 -c ''  ->  python3: /lib/aarch64-linux-gnu/libm.so.6: version `GLIBC_2.38' not found
                            (required by /usr/local/bin/../lib/libpython3.14.so.1.0)
/usr/bin/python3 --version  ->  Python 3.11.2 (the image's own, works)
ldd --version               ->  Debian GLIBC 2.36-9+deb12u13
```

It is not a dpkg package and not uv-managed (`~/.local/share/uv/python` is empty, `uv python list` shows 3.14 as "download available"), so the copied stage is the only source. Ralph's own orchestrator is unaffected — it runs through `uv run`, which fetches its own interpreter — which is why this stayed invisible.

Second, the hook. `templates/git-hooks/pre-commit` selects its NFC normalizer by lookup, not by execution:

```bash
if printf '' | iconv -f utf-8-mac -t utf-8 >/dev/null 2>&1; then ...        # macOS BSD iconv
elif command -v python3 >/dev/null 2>&1; then                              # finds the broken one
  to_nfc() { python3 -c 'import sys, unicodedata; ...' "$1"; }
```

Inside the container the `iconv` branch is unavailable (glibc iconv has no `utf-8-mac`), so the `python3` branch is always taken, `nfc=$(to_nfc "$p")` exits non-zero, and `set -euo pipefail` aborts the hook. The check runs on any non-empty stage once `HEAD` exists, so it is every commit, not an edge case.

A downstream project (Documentation type) carries a local deviation in its copy of the hook — the candidate is chosen by running it (`for cand in python3 /usr/bin/python3; do "$cand" -c '' ... `) — and that is the only reason its container commits work. Upgrade mode U4 overwrites the hook from the template, so the deviation was wiped by its 0.6.0 upgrade and had to be restored by hand; it will be wiped again by the next one. Absorbing both fixes here is what lets that project take the template file verbatim again, and stops every newly bootstrapped Documentation/Python project from shipping a container in which Ralph cannot commit.

Verification note worth keeping: **the host cannot show this defect.** On macOS BSD `iconv` ships `utf-8-mac`, the first branch wins and `python3` is never reached, so a host commit passes under either version of the hook. The proof is a commit made inside the container.

## Scope

In scope:
- Make the interpreter that lands in the image runnable — pin the copied stage to a base that matches `node:20` (bookworm), or stop copying an interpreter into `/usr/local` at all and leave the image's own `python3` first in `PATH`.
- Make `templates/git-hooks/pre-commit` choose the NFC normalizer by executing the candidate interpreter, not by `command -v`, and keep the "no normalizer at all" bail-out.
- Cover both with tests next to the existing ones, so a future tag bump or template edit cannot silently reintroduce either half.

Out of scope:
- The `~/.claude` binding for plugin resolution — that is TASK-240.
- Anything in the downstream project's own repository.
- Changing what the NFC check itself does; only how the normalizer is selected.

## Files

- `plugins/ralph/skills/ralph-init/templates/devcontainer/lang/Dockerfile.lang.docs` (exists) — declares the `python:3.14` stage for Documentation projects
- `plugins/ralph/skills/ralph-init/templates/devcontainer/lang/Dockerfile.lang.python` (exists) — the same declaration for Python projects
- `plugins/ralph/skills/ralph-init/templates/devcontainer/lang/Dockerfile.install.docs` (exists) — copies the stage's `/usr/local` into the image
- `plugins/ralph/skills/ralph-init/templates/devcontainer/lang/Dockerfile.install.python` (exists) — the same copy for Python projects
- `plugins/ralph/skills/ralph-init/templates/devcontainer/Dockerfile.base` (exists) — the `node:20` base whose glibc the copied interpreter must match
- `plugins/ralph/skills/ralph-init/templates/git-hooks/pre-commit` (exists) — the normalizer selection
- `tests/unit/pre-commit-hook.bats` (exists) — where the hook's selection behaviour belongs
- `tests/unit/devcontainer-claude-share.bats` (exists) — pattern to follow for a fragment assertion

## Source

Source: /Users/paul/Private/Alfa/Projects/enterprise@0ceb7f0c4f6c

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
- [x] #1 The language fragments no longer introduce an interpreter incompatible with Dockerfile.base: either the copied Python stage is pinned to a Debian-bookworm-based tag matching node:20, or the COPY into /usr/local is dropped so the image's own python3 stays first in PATH - verified by grep over Dockerfile.lang.docs, Dockerfile.lang.python, Dockerfile.install.docs and Dockerfile.install.python
- [x] #2 A test asserts the language fragments cannot copy an interpreter built against a newer Debian than Dockerfile.base uses, so a tag bump cannot silently reintroduce the mismatch
- [x] #3 templates/git-hooks/pre-commit selects the NFC normalizer by running the candidate interpreter, and a python3 earlier in PATH that fails to start no longer aborts the hook
- [x] #4 tests/unit/pre-commit-hook.bats covers that selection with a stub python3 that exits non-zero, and asserts the NFC duplicate check still BLOCKS rather than degrading to a silent pass
- [x] #5 The new stub-python3 test does not depend on filesystem Unicode normalization, and the task notes state the baseline: on a normalization-collapsing volume (macOS APFS) the two pre-existing NFD/NFC duplicate tests cannot pass because both names resolve to one file, while on the container ext4 they do pass - so no-new-failures is judged against the environment the suite actually ran in
- [x] #6 The live-container outcomes are recorded as pending host-side verification rather than checked off blind: the notes state that python3 -c '' exiting 0 in a freshly built devcontainer, and a successful commit plus a refused NFD duplicate inside one, could not be verified from the autonomous run because the devcontainer mounts no docker socket and this repo's own Dockerfile carries no python:3.14 stage
- [x] #7 uv run pytest passes, uv run ruff check . passes, and LC_ALL=C bats tests/unit passes with no new failures beyond the environment-dependent baseline named in AC 5; shell edits satisfy the R5 GNU/BSD portability rule
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
AC REWORK before start (handoff acceptance gate, 2026-09-27). The handoff's diagnosis verified cleanly against this repo: Dockerfile.base:6 is FROM node:20; Dockerfile.lang.docs:4 and Dockerfile.lang.python:4 declare FROM python:3.14 AS python-runtime; Dockerfile.install.docs:2 and Dockerfile.install.python:2 COPY --from=python-runtime /usr/local /usr/local; templates/git-hooks/pre-commit:47 selects by 'elif command -v python3' rather than by execution. All seven (exists) paths are present and no dependencies are listed. Three problems were found that the original ACs did not survive, hence this rework. (1) Original AC 1 and AC 5 required a freshly built devcontainer, but .devcontainer/devcontainer.json mounts no docker socket, so an autonomous run executing inside the container cannot build or run another container; compounding it, this repo's own Dockerfile carries no python:3.14 stage, so even with docker access a build here would not exercise the defect - proper live verification needs a scaffolded throwaway docs or python project. Those two ACs were therefore replaced by a static fragment assertion plus an explicit pending-host-verification record. (2) Original AC 6 gated only on pytest and ruff while AC 4 ADDS bats tests, so the gate structurally could not see whether the new tests pass - the same hole that let TASK-239 ship a dangling reference; bats is now in the gate. (3) The two pre-existing bats failures in pre-commit-hook.bats (globally 53 and 54) are filesystem-dependent, not hook bugs: creating an NFD and an NFC filename on this host yields ONE file, verified directly, so the duplicate the test needs cannot exist, git add stages the same path, the hook correctly exits 0 and the status -eq 1 assertion fails. On container ext4 both names are distinct and the tests pass. That asymmetry is now stated as the baseline so the implementer does not chase a phantom.

Plan: (1) Drop the foreign python-runtime stage entirely — Dockerfile.lang.docs/.python declared FROM python:3.14 (trixie, glibc 2.38+) and Dockerfile.install.docs/.python copied its /usr/local over a bookworm node:20 base. Dockerfile.base already installs uv and runs 'uv python install 3.14' unconditionally for every language, and both project types drive Python through 'uv run', so the copied interpreter is redundant as well as unrunnable; removing it leaves the image's own /usr/bin/python3 first in PATH and removes the glibc coupling instead of re-pinning a tag that cannot be verified offline. (2) Add tests/unit/devcontainer-python-runtime.bats asserting the invariant generically: no lang fragment may copy a whole /usr/local from a foreign stage unless both that stage's image and Dockerfile.base's base image pin the same explicit Debian suite — so a future re-pin is allowed but a bare 'FROM python:3.14' cannot come back. (3) Rewrite the pre-commit normalizer selection to probe candidates by execution ('$cand' -c 'import unicodedata') instead of 'command -v python3', keeping the bail-out. (4) Mirror the new hook into .git/hooks/pre-commit (template-parity.bats:52 pins them exact). Baseline for AC 5/7 measured on this container (ext4): bats tests/unit 143 ok / 1 not ok (#130 'R11: settings.local.json keeps the template JSON shape', pre-existing and unrelated); both NFD/NFC duplicate tests PASS here; pytest 498 passed; ruff clean.

Implemented. (1) Fragments: Dockerfile.lang.docs / Dockerfile.lang.python no longer declare any FROM stage, and Dockerfile.install.docs / Dockerfile.install.python no longer COPY --from=python-runtime /usr/local /usr/local; they keep only the uv binary copy. The base image's own /usr/bin/python3 therefore stays first in PATH and the uv-managed 3.14 that Dockerfile.base installs unconditionally remains the interpreter every project type actually uses through 'uv run'. Re-pinning to python:3.14-bookworm was the alternative AC 1 allows; dropping the copy was chosen because the tag's existence cannot be verified from inside this container (no registry access) and because the copy is redundant given 'uv python install 3.14' at Dockerfile.base:90. (2) New tests/unit/devcontainer-python-runtime.bats (6 tests) implements the invariant as a reusable check: a COPY --from landing in /usr/local, /usr/local/bin or /usr/local/lib is a violation unless the source stage's image and Dockerfile.base's base image pin the SAME explicit Debian suite. /usr/local/go and the single-file uv copy are explicitly allowed (a positive-control test pins that). Because the shipped fragments now contain no guarded copy, the guard is exercised against a synthetic reproduction of the exact old defect (FROM python:3.14 + COPY /usr/local, base FROM node:20) and asserted to FAIL - and to still fail when only one side is pinned, or when both are pinned to different suites, and to pass only when both say bookworm. So the assertion is not vacuous. (3) templates/git-hooks/pre-commit now probes candidates by execution: for cand in python3 /usr/bin/python3 python /usr/bin/python; do command -v "$cand" && "$cand" -c 'import unicodedata'; done, first success wins; the 'no normalizer at all' bail-out is kept (message reworded) and exits 0 as before. The live .git/hooks/pre-commit was re-copied from the template because template-parity.bats:52 pins them 'exact' (that path is untracked, so it carries no commit). (4) Three tests appended to pre-commit-hook.bats. The NFC/NFD fixture is built with git hash-object + git update-index --cacheinfo, so no file is ever written to the working tree and the test is independent of filesystem normalization (AC 5): it passes on macOS APFS as well, where the two pre-existing on-disk duplicate tests cannot. Regression proof: run against a reconstructed pre-fix hook, all three new tests FAIL (blocked -> abort), and they pass against the fixed one. R5: only command -v, for, case, awk, sed -nE and grep -E are used; no GNU-only flags, no grep -P, no sed -i, no readlink -f.

PENDING HOST-SIDE VERIFICATION (AC 6) - not checked off blind. Two outcomes could not be observed from this autonomous run: (a) python3 -c '' exiting 0 inside a freshly built devcontainer scaffolded from the docs or python templates, and (b) a successful commit plus a refused NFD duplicate made from inside such a container. Reason: .devcontainer/devcontainer.json mounts no docker socket, so a run executing inside the container cannot build or start another container; and this repo's own .devcontainer/Dockerfile is the Go flavour with no python:3.14 stage, so even with docker access a build here would not exercise the defect - proper live verification needs a throwaway docs or python project scaffolded by ralph-init on the host. What WAS verified in this environment: the four fragments no longer reference python:3.14 or copy /usr/local; the hook falls through a python3 that exits non-zero and still BLOCKS the duplicate; LC_ALL=C bats tests/unit 152 ok / 1 not ok - the single failure is #139 'R11: settings.local.json keeps the template's JSON shape', pre-existing and unrelated (it failed identically at baseline as #130, before any edit in this task); uv run pytest 498 passed; uv run ruff check . clean; bats tests/integration 52/52. Baseline note for AC 5: on this container (ext4) the two pre-existing on-disk NFD/NFC duplicate tests PASS, so no-new-failures is judged against 143 ok / 1 not ok before and 152 ok / 1 not ok after (+9 new tests, all passing). On macOS APFS those two would fail for filesystem reasons; the three tests added here would not.

Commit: `ff8ff17` - task-242: ship a runnable python3 in the devcontainer and pick the NFC normalizer by execution

Review follow-up (task-reviewer, CHANGES REQUESTED -> fixed): removed the leftover unpinned '# Ruby: COPY --from=ruby /usr/local /usr/local' hint in .devcontainer/Dockerfile (the pinned example had been added beside it rather than replacing it, leaving two contradictory hints with the anti-pattern last) and pinned the Java hint the same way; retitled the now-empty 'Stage 1' banner in both lang fragments to 'Language Runtime (none - Python comes from the base image)'. Correction to the AC 5 claim above: the new fixture does not touch the working tree, so it does not depend on filesystem normalization; a macOS pass was NOT verified from this container - on macOS git may precompose command-line arguments, though the test's setup sets core.precomposeunicode false.

Commit: `2e2bf66` - task-242: drop the unpinned runtime-copy hints and retitle the empty language stage

task-reviewer verdict: APPROVED (re-review after 2e2bf66). Final gates on the branch tip: uv run pytest 498 passed, uv run ruff check . clean, LC_ALL=C bats tests/unit 152 ok / 1 not ok (#139 only, the pre-existing container artifact of the masked .claude/ - absent on a clean master clone), bats tests/integration 52/52.

Commit: `2f257da` - task-242: bump plugin version to 0.6.3 (patch)
<!-- SECTION:NOTES:END -->
