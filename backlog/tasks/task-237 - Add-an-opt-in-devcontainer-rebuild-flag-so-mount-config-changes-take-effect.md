---
id: TASK-237
title: Add an opt-in devcontainer rebuild flag so mount config changes take effect
status: Done
assignee: []
created_date: '2026-09-04 17:58'
updated_date: '2026-09-04 18:09'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Verified this session: ralph-run's devcontainer bring-up (`plugins/ralph/skills/ralph-run/scripts/ralph/devcontainer.py`, function `start_devcontainer`) runs a bare `devcontainer up --workspace-folder <ws>`, which REUSES any existing container. devcontainer.json mount/config changes therefore do NOT take effect on a reused container — they apply only at container CREATION.

Concretely: TASK-235 added a `.venv` volume overlay to keep the container virtualenv off the host bind mount, but the very next devcontainer run (TASK-236) reused the pre-fix container, so the overlay was ignored and the host `.venv` was clobbered again. The @devcontainers/cli supports `--remove-existing-container` on `up` to force a fresh container. Today the only way to activate a mount change is a manual `devcontainer up --workspace-folder . --remove-existing-container` outside ralph.sh.

Current code (for reference):

```python
result = subprocess.run(
    ["devcontainer", "up", "--workspace-folder", str(workspace_folder)],
    check=False, capture_output=True, text=True,
)
```

Fix direction: add an opt-in orchestrator flag (proposed name `--rebuild`) that, when set together with `--devcontainer`, appends `--remove-existing-container` to that `devcontainer up` argv. Default OFF (a rebuild is expensive; normal runs keep reusing the container). Wire it through the arg parser (`plugins/ralph/skills/ralph-run/scripts/ralph/args.py`) and `start_devcontainer()`, surface it in the ralph-run SKILL.md devcontainer/knobs section and the README flag table, and add a unit test. Image-level rebuild (`--build-no-cache` for Dockerfile changes) is OUT of scope — mount recreation is all the .venv overlay needs.

Parity/governance: these are shipped `plugins/ralph/**` files, so the merge triggers `bump-version.sh --auto` (plugin version bump). devcontainer.py / args.py / the ralph-run SKILL.md are the plugin itself and are NOT mirrored to ralph-init templates (only `.devcontainer/` is, and this task does not change it) — so no ralph-init Init/Upgrade parity is required; confirm and note that.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A new opt-in flag --rebuild (default off) is accepted by the ralph-run orchestrator arg parser and is a no-op unless --devcontainer is also set
- [x] #2 With --devcontainer --rebuild set, start_devcontainer() invokes 'devcontainer up --workspace-folder <ws> --remove-existing-container'; without --rebuild the argv stays exactly 'devcontainer up --workspace-folder <ws>' (unchanged from today)
- [x] #3 A unit test pins both argv shapes (with and without --rebuild), mirroring the style of test_loop_devcontainer_up.py
- [x] #4 ralph-run SKILL.md documents the flag in its devcontainer/knobs section, and the README flag table lists --rebuild
- [x] #5 Task notes confirm no ralph-init template parity is needed because the changed files are plugin code, not templates
- [x] #6 uv run pytest and uv run ruff check . pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) args.py — add `--rebuild` (store_true, default False) to build_parser, a `rebuild: bool = False` field on ParsedArgs, and wire it through parse(). (2) devcontainer.py — start_devcontainer() gains a keyword-only `rebuild: bool = False`; when True the argv becomes `devcontainer up --workspace-folder <ws> --remove-existing-container`, otherwise byte-identical to today. (3) loop.py — pass `rebuild=args.rebuild` at the single call site (guarded by `if args.devcontainer`, which is what makes --rebuild a no-op without --devcontainer). refine/loop.py keeps the default (out of scope). (4) New tests/test_devcontainer_rebuild.py pinning BOTH argv shapes plus the loop-level pass-through and the no-op-without-devcontainer case. (5) Docs: ralph-run SKILL.md knobs table + Step 4 conditional flag; README CLI options table row. (6) Verify no ralph-init parity needed via tests/unit/template-parity.bats manifest (plugin code is not mirrored). (7) uv run pytest + uv run ruff check .

AC #5 — ralph-init template parity NOT required, verified against the R11 manifest in tests/unit/template-parity.bats. The mirror set (exact_pairs) is: .claude/hooks/*.sh, .claude/brainstorm-rules.md, ralph.sh, refine.sh, a CLAUDE.md region, .git/hooks/{post-commit,commit-msg,pre-commit}, and .devcontainer/{devcontainer.json,init-firewall.sh}. Every file this task touches — scripts/ralph/args.py, scripts/ralph/devcontainer.py, scripts/ralph/loop.py, tests/test_devcontainer_rebuild.py and ralph-run/SKILL.md — lives under plugins/ralph/ and is plugin code DISTRIBUTED via the marketplace, not bootstrap content copied into a consumer project, so none of it has a templates/ counterpart. The bats case 'R11: the canonical orchestrators are outside the shim mirror set' asserts exactly this for the orchestrator, and 'R11: plugin-bundled agents are distributed, not mirrored' states the same principle for the plugin's agents. .devcontainer/ IS mirrored, but this task does not change it (the flag only alters the devcontainer CLI argv). Full tests/unit bats run: 115/115 pass, template-parity included.

Commit: `010833e` - task-237: add an opt-in --rebuild flag to recreate the devcontainer

Implemented. `--rebuild` (store_true, default off) is parsed in args.py and carried on ParsedArgs as `rebuild: bool = False`; loop.py forwards it as `start_devcontainer(project_root, rebuild=args.rebuild)` at the single call site, which sits inside `if args.devcontainer:` — that guard is what makes the flag structurally a no-op without --devcontainer, rather than a validation error. In devcontainer.py the argv is now built into a local list and gains `--remove-existing-container` only when rebuild=True; the off-path argv and its 'Starting devcontainer...' / 'Devcontainer is ready.' output are byte-identical to master. The rebuild path prints 'Rebuilding devcontainer (removing existing container)...' instead, so the expensive path is visible in the log. New tests/test_devcontainer_rebuild.py (11 cases) pins both argv shapes, the omitted-keyword default, parser acceptance/ordering/abbreviation, loop pass-through of True and False, and the no-devcontainer no-op. Docs: ralph-run SKILL.md gets a knobs-table row, an explanatory paragraph, an example invocation and a Step 4 conditional-append rule; README gets a CLI-options row, a cross-reference from the TASK-235 .venv-isolation paragraph, and the new test file in its test inventory. Out of scope by task decision, unchanged and confirmed harmless: image-level rebuild (--build-no-cache) and the separate refine entry point (scripts/ralph/refine/loop.py), which keeps the rebuild=False default — a /ralph-refine run after a devcontainer.json edit still reuses its container, worth a follow-up task if refine runs become common. Verification: uv run pytest 498 passed; uv run ruff check . clean; LC_ALL=C bats tests/unit/ 115/115. task-reviewer verdict APPROVED, with R11 template parity independently re-derived from git ls-files over the ralph-init templates tree (no counterpart exists for any touched file) rather than taken from the task's own claim.

Commit: `9ccfd69` - task-237: bump plugin version to 0.5.0 (minor)
<!-- SECTION:NOTES:END -->
