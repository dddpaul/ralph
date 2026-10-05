---
id: TASK-273
title: >-
  Detect and patch the broad sudoers chown and the early CLAUDE_CODE_VERSION ARG
  in assembled Dockerfiles on upgrade
status: In Progress
assignee: []
created_date: '2026-10-05 18:16'
updated_date: '2026-10-05 18:34'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

TASK-271 narrowed the devcontainer sudoers rule and TASK-272 moved `ARG CLAUDE_CODE_VERSION` next to the npm step, but both changed only the template (`plugins/ralph/skills/ralph-init/templates/devcontainer/Dockerfile.base`) and this repo's `.devcontainer/Dockerfile`. Every project bootstrapped earlier keeps the old text, because Upgrade Mode U2 marks `.devcontainer/Dockerfile` as `skipped (assembled)` and never re-syncs it:

- **Broad sudoers chown.** The image grants `node` an unrestricted `/bin/chown`. With it, `node` can take over `/usr/local/bin/init-firewall.sh`, which `node` may run as root, and so gets root and can drop the firewall. The current template grants only `/bin/chown node\:node /workspace/.venv`, the exact command `postCreateCommand` runs, and validates the file with `visudo -cf`.
- **Early ARG.** `ARG CLAUDE_CODE_VERSION` declared at the top of the final stage invalidates every later `RUN` when the version changes, so each Claude Code bump rebuilds the whole image. Measured downstream (stacks): about an hour per bump for its 4.6 GB docs image. Declared right before `LABEL dev.ralph.claude-code-version`, a bump re-runs only the npm step and those after it (verified in TASK-272 AC #5).

The same Upgrade Mode already handles two older Dockerfile defects with this pattern: `stale-runtime-copy.sh` (check + patch) and `floating-uv-copy.sh` (check). Follow it for both new checks.

## Design

Two scripts, one per condition, following the `plugins/ralph/skills/ralph-init/scripts/stale-runtime-copy.sh` contract: `check` prints one line per finding (exit 0 = clean, 1 = found); `patch` prints the patched Dockerfile on stdout and never writes the file (exit 0 = patched text printed, 1 = nothing to patch, 3 = patch by hand, nothing printed); exit 2 = usage error or unreadable input. Parse instructions with continuation lines joined and comments dropped, as the existing scripts do.

```text
plugins/ralph/skills/ralph-init/scripts/broad-sudoers-chown.sh   check <Dockerfile> | patch <Dockerfile> <devcontainer.json>
plugins/ralph/skills/ralph-init/scripts/early-claude-arg.sh      check <Dockerfile> | patch <Dockerfile>
tests/python/test_upgrade_broad_sudoers_chown.py
tests/python/test_upgrade_early_claude_arg.py
```

**broad-sudoers-chown.sh.** Finding: the `echo "node ALL=(root) NOPASSWD: ..." > /etc/sudoers.d/node-firewall` grant contains `/bin/chown` followed directly by the closing quote or a comma, i.e. chown with no fixed arguments. `patch` replaces that grant with exactly the template's line and appends `&& visudo -cf /etc/sudoers.d/node-firewall` when it is missing:

```dockerfile
 && echo "node ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh, /bin/chown node\:node /workspace/.venv" > /etc/sudoers.d/node-firewall \
 && chmod 0440 /etc/sudoers.d/node-firewall \
 && visudo -cf /etc/sudoers.d/node-firewall
```

Exit 3 (patch by hand) when the grant lists any command other than `init-firewall.sh` and the bare chown, or when the project's `devcontainer.json` `postCreateCommand` runs a `sudo` command other than `sudo chown node:node /workspace/.venv`. In that case narrowing would break the container's setup command. A `postCreateCommand` with no `sudo` at all is fine.

**early-claude-arg.sh.** Finding: in the final stage, a `RUN` lies between `ARG CLAUDE_CODE_VERSION` and the `RUN` that installs `@anthropic-ai/claude-code@`. This is the same rule `placement_problems()` in `tests/python/test_devcontainer_claude_code_pin.py` enforces. `patch` removes the `ARG` line together with its directly preceding `# No default on purpose ...` comment paragraph, and re-inserts both immediately before `LABEL dev.ralph.claude-code-version`, or before the npm `RUN` when the `LABEL` is absent. Exit 3 when the `ARG` has a default, appears more than once in the final stage, or the npm `RUN` is missing. A pre-pin `ARG CLAUDE_CODE_VERSION=latest` is the existing version-pin patch's job (Upgrade Mode, "Claude Code version pin on upgrade", step 2, which since TASK-272 already places the `ARG` before the `LABEL`).

**Upgrade Mode wiring** in `plugins/ralph/skills/ralph-init/SKILL.md`:
- **U2 row 12:** run both checks next to the existing ones. Status suffixes: `early claude-code arg` and `broad sudoers chown`.
- **U4:** offer each patch confirm-only, with the same shape as the uv pin patch: build the text, show the diff, write on a yes. For the early `ARG`, when the version-pin patch is accepted in the same run, re-run `early-claude-arg.sh check` on the result and make no separate offer if it is clean.
- **U5 labels:** `claude arg moved` / `early claude-code arg, user declined` / `early claude-code arg, patch by hand`, and `sudoers narrowed` / `broad sudoers chown, user declined` / `broad sudoers chown, patch by hand`. Join them after the existing ones in this order: version pin, claude arg, uv pin, runtime copy, sudoers. U2 re-derives the statuses from the Dockerfile on every run, so a declined patch is offered again.
- **U5 summary:** when either patch was written, tell the user that the image needs a rebuild (`/ralph-run rebuild=true` or "Rebuild Container"). When the `ARG` moved, also say that this first rebuild redoes every step once, and later bumps rebuild only the tail.

## Out of scope

- Init (Step 3.x): new projects already get the fixed template from TASK-271/272.
- Surfacing these findings in the preflight drift warning (`managed-file-drift.sh` does not cover the assembled Dockerfile).
- Patching downstream projects themselves. They pick this up through `/ralph-init upgrade` after release.

## Host checks

The scripts are bash and run on macOS hosts during upgrade. R-INFRA-3 applies: GNU/BSD userland and `/bin/bash` 3.2. Ralph's Linux container has neither BSD tools nor `docker`, so the last two ACs run on the macOS host after the Ralph run, before Done. The "old" fixture for the Docker check is the template as it was before TASK-271 and TASK-272, which carries both defects:

```bash
git show 39adcb5:plugins/ralph/skills/ralph-init/templates/devcontainer/Dockerfile.base
```
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 broad-sudoers-chown.sh check exits 1 on a Dockerfile whose node-firewall grant has a bare /bin/chown and 0 on the current Dockerfile.base and on this repo's .devcontainer/Dockerfile — verified by tests/python/test_upgrade_broad_sudoers_chown.py
- [x] #2 broad-sudoers-chown.sh patch prints the Dockerfile with the grant narrowed to /bin/chown node\:node /workspace/.venv and visudo -cf appended, all other lines unchanged; it exits 3 with nothing printed on a grant listing another command and on a devcontainer.json whose postCreateCommand runs a different sudo command — verified by tests
- [x] #3 early-claude-arg.sh check exits 1 when a RUN lies between ARG CLAUDE_CODE_VERSION and the npm RUN in the final stage, and 0 on the current Dockerfile.base and on this repo's .devcontainer/Dockerfile — verified by tests/python/test_upgrade_early_claude_arg.py
- [x] #4 early-claude-arg.sh patch moves the ARG and its 'No default on purpose' comment paragraph to immediately before LABEL dev.ralph.claude-code-version (before the npm RUN when the LABEL is absent), all other lines unchanged; it exits 3 with nothing printed on an ARG with a default, a duplicated ARG, or a missing npm RUN — verified by tests
- [x] #5 The pre-TASK-271 template (git show 39adcb5:…/Dockerfile.base) with both patches applied passes placement_problems() from test_devcontainer_claude_code_pin.py and the grant checks of test_devcontainer_sudoers.py — verified by a test
- [x] #6 plugins/ralph/skills/ralph-init/SKILL.md Upgrade Mode runs both checks in U2 row 12, offers each patch confirm-only in U4 (early-ARG offer skipped when the version-pin patch already placed the ARG), and documents the U5 labels in the order version pin, claude arg, uv pin, runtime copy, sudoers
- [x] #7 The U5 summary text tells the user to rebuild the image when either patch was written, and states that moving the ARG costs one full rebuild after which a bump rebuilds only the tail
- [ ] #8 On the macOS host, both new pytest files and tests/python/test_bash32_syntax.py pass with /bin/bash 3.2 and /usr/bin sed, grep and awk first on PATH; the output is recorded in the task notes
- [ ] #9 On the macOS host, the 39adcb5 template assembled as the node flavour and patched by both scripts builds with docker buildx, and docker run --rm --user node <image> sudo -n -l lists exactly init-firewall.sh and /bin/chown node\:node /workspace/.venv; the output is recorded in the task notes
- [x] #10 uv run ruff check . is clean, uv run pytest passes and LC_ALL=C node_modules/.bin/bats tests/unit passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: two self-contained bash+awk scripts in plugins/ralph/skills/ralph-init/scripts/ following the stale-runtime-copy.sh contract (check/patch, exit 0/1/2/3, patch only prints). Both join backslash continuations and drop comment lines to find instructions, then edit physical lines. broad-sudoers-chown.sh: finding = the node-firewall echo grant lists a bare /bin/chown; patch rewrites the quoted grant on its physical line to the template's and appends ' \\' + ' && visudo -cf ...' to the instruction's last line when missing; by hand (3) when the grant is not exactly {init-firewall.sh, bare chown}, the echo spans lines, there are several grants, or devcontainer.json postCreateCommand runs any sudo other than 'sudo chown node:node /workspace/.venv' (or is not a one-line string). early-claude-arg.sh: finding = a RUN between the first final-stage ARG CLAUDE_CODE_VERSION and the npm RUN; patch moves the ARG and its 'No default on purpose' comment run (plus the now-doubled blank line) to right before LABEL dev.ralph.claude-code-version, else before the npm RUN; by hand on a default, a duplicate, a missing npm RUN, or a RUN still left between the insertion point and npm. Tests mirror test_upgrade_stale_runtime_copy.py incl. mawk run; AC #5 test feeds the 39adcb5 template through both patches into placement_problems()/rule_problems(). SKILL.md: U2 row 12, U3 pending-work bullets, U4 two confirm-only offers, U5 labels+order+rebuild text. AC #8/#9 need the macOS host (no BSD userland/docker here).

Commit: `3e71dee` - task-273: detect and patch the broad sudoers chown and the early CLAUDE_CODE_VERSION ARG on upgrade

Commit: `3c2929f` - task-273: list every patch-by-hand reason of the sudoers patch in Upgrade Mode

Review: ralph:task-reviewer APPROVED (score 8), 0 blocking. Minor 2 fixed (SKILL.md now lists all exit-3 reasons of the sudoers patch). Minor 1 kept on purpose: a postCreateCommand that is not a one-line string (e.g. array form) exits 3 even without sudo — conservative, and U4 runs the patch after devcontainer.json is rewritten to the template's string form. Gates in container: uv run ruff check . clean; uv run pytest 870 passed, 3 skipped; bats tests/unit 154 tests, only #140 (settings.local.json shape) fails, caused by this checkout's local .claude/settings.local.json — reviewer confirmed 0 failures in a clean worktree at HEAD and on master.

Not marked Done and not merged: AC #8 and #9 need the macOS host (no BSD userland, /bin/bash 3.2 or docker in the container). Host steps: (8) PATH=/usr/bin:/bin:$PATH BASH32_SYNTAX_SHELL=/bin/bash uv run pytest tests/python/test_upgrade_broad_sudoers_chown.py tests/python/test_upgrade_early_claude_arg.py tests/python/test_bash32_syntax.py (confirm 'bash' resolves to /bin/bash 3.2 and awk/sed/grep to /usr/bin); (9) git show 39adcb5:plugins/ralph/skills/ralph-init/templates/devcontainer/Dockerfile.base, replace {{LANGUAGE_STAGE}}/{{LANGUAGE_INSTALL}} with lang/Dockerfile.lang.node / Dockerfile.install.node, run early-claude-arg.sh patch then broad-sudoers-chown.sh patch <file> templates/devcontainer/devcontainer.json, build with docker buildx (--build-arg CLAUDE_CODE_VERSION=<pin> UV_VERSION=<pin> TZ=UTC, context with init-firewall.sh), then docker run --rm --user node <image> sudo -n -l must list exactly /usr/local/bin/init-firewall.sh and /bin/chown node\:node /workspace/.venv. Record both outputs here, check AC #8/#9, then Done + Merge step 6 (bump-version.sh --auto will bump: shipped plugins/ralph files changed).
<!-- SECTION:NOTES:END -->
