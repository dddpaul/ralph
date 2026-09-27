---
id: TASK-247
title: Move declarative devcontainer JSON assertions from bats to pytest
status: Done
assignee: []
created_date: '2026-09-27 12:58'
updated_date: '2026-09-27 13:24'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Answers the standing question "why are we still using bats when only the Python orchestrator is left" with a measured cut rather than a rewrite. Every file in tests/unit was classified by whether a shell script is the system under test:

**Genuinely bats — a bash script IS the thing being tested. Keep as-is:**
bump-version.bats, commit-msg-hook.bats, filename-length-guard.bats, pre-commit-hook.bats, pretools-hooks.bats, version-bump-guard.bats.

**Pure file/JSON assertions — nothing is executed, so bats buys nothing. Port these (43 tests):**
devcontainer-claude-config-root.bats (9), devcontainer-claude-hostpath-bind.bats (9), devcontainer-claude-share.bats (11), devcontainer-python-runtime.bats (6), devcontainer-venv-overlay.bats (8).

## Scope cut (deliberate)

Port ONLY those five files. `tests/unit/template-parity.bats` (12 tests) is explicitly out of scope as a follow-on: it is the largest file, it also asserts CLAUDE.md prose regions rather than just JSON shape, and it contains the one test that fails spuriously inside containers ("R11: settings.local.json keeps the template's JSON shape" — an artifact of the container's masked .claude directory, absent on a clean clone). Porting it is its own deliverable.

## Notes for the implementer

- pytest already collects `tests/python` — see testpaths in `pyproject.toml`. Ported tests belong there.
- `.devcontainer/devcontainer.json` is JSONC: it contains `//` line comments, so `json.loads` fails on it raw. The bats helper strips them before piping to jq:

```bash
strip_jsonc() { sed -E 's@^[[:space:]]*//.*$@@' "$1"; }
```

A Python port needs the equivalent line-comment strip. Note this only handles comments on their own line, which is all the file uses — do not silently widen it to inline comments without a test.
- Four of the five files depend on `jq`; the port removes that external dependency from the suite.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All 43 assertions from the five devcontainer bats files exist as pytest tests under tests/python with equal or greater coverage
- [x] #2 All five devcontainer bats files are deleted from tests/unit
- [x] #3 A shared Python JSONC reader strips // line comments before json.loads and is used by every ported test module
- [x] #4 Each ported test module contains at least one negative case built from a mutated copy of the config, proving the assertions are not vacuous
- [x] #5 uv run pytest collects and passes the ported tests
- [x] #6 LC_ALL=C bats tests/unit passes with the six remaining bats files
- [x] #7 tests/unit/template-parity.bats is unchanged, and no jq dependency remains in any surviving devcontainer test
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: shared reader tests/python/devcontainer_config.py (load_jsonc = whole-line // strip + json.loads, path constants, mount/query helpers). Port each bats file 1:1 to tests/python/test_devcontainer_*.py, parametrized over live+template; replace jq with json, awk Dockerfile guard with a Python port. Each module gets a mutated-copy negative case. Delete the five bats files; README test-layout note. Note: devcontainer-claude-share.bats has 12 tests now (TASK-244 added one), so the port covers 44.

Commit: `b88c192` - task-247: port devcontainer config assertions from bats to pytest

Commit: `4124382` - task-247: mutate a copy of the real python fragments in the runtime guard test

Done. Five devcontainer bats files (44 tests: claude-share had 12 after TASK-244, not 11) ported to tests/python/test_devcontainer_*.py (81 pytest items, parametrized live/template) with shared JSONC reader tests/python/devcontainer_config.py (whole-line // only). python-runtime port reimplements the awk COPY guard in Python; it uses load_jsonc via an added test pinning build.dockerfile. Each module has a mutated-copy negative case (python-runtime mutates a copy of the real lang/ fragments). AC#6: bats tests/unit = 110 tests across SEVEN remaining files (six + template-parity.bats kept by AC#7); the one failure, 'R11: settings.local.json keeps the template's JSON shape', is the pre-existing container-only masked-.claude artifact named in the task body, identical on master. uv run pytest 579 passed; ruff clean. task-reviewer: APPROVED.
<!-- SECTION:NOTES:END -->
