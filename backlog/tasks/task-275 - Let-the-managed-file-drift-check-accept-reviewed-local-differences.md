---
id: TASK-275
title: Let the managed-file drift check accept reviewed local differences
status: Done
assignee: []
created_date: '2026-10-05 19:02'
updated_date: '2026-10-05 19:28'
labels: []
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

ralph-run's preflight runs `plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh check <project>`. It prints `WARNING: ralph-init managed file behind the installed plugin — <path>: outdated` for every managed file that differs from the installed plugin's template. In this repo, two files differ on purpose and warn on every launch:

- `CLAUDE.md`: Task Lifecycle step 6 adds the `bump-version.sh --auto` / `--tag` steps, which are plugin-marketplace governance and documented as NOT mirrored to the ralph-init templates.
- `.git/hooks/post-commit`: adds the TASK-217 auto-bump nudge, a call to `.claude/hooks/bump-version.sh --nudge`.

A warning that is always on trains people to ignore it, which defeats the check. Any project with a reviewed, deliberate deviation hits the same problem.

## Design

Use an acceptance list keyed by content hashes, not a plain ignore list. An ignore list would also hide a later real change. An acceptance records the exact pair of contents that was reviewed, so the warning comes back as soon as either side changes. In particular it comes back when a new plugin release changes the template, which is when the deviation needs another look.

```text
.claude/managed-file-drift.accept
```

Format: one line per accepted path; blank lines and `#` comments are allowed:

```text
<path> template=<sha256> project=<sha256>
```

- **check:** a managed path listed with both hashes equal to the current values is not reported. Any mismatch reports it as `outdated` as before.
- **Hashed bytes:** each hash covers exactly what the path's rule compares. That is the whole file for `exact`, `allow` and `runargs`, each hook file for `hooks`, and only the lines above the heading for `above:<h>`. So editing the `## Project-Specific` section of `CLAUDE.md` does not void the acceptance.
- **accept:** new subcommand `managed-file-drift.sh accept <project-dir> <path>` prints the line for the current pair on stdout. It exits 2 with a reason when the path is not in the managed table or is not currently drifting. It never writes the file; the user appends the line.
- **Malformed line:** check exits 2 naming the file and line number. Preflight already relays exit 2 as `WARNING: could not check ralph-init managed files — <reason>`, so a typo is visible instead of silently dropping the check.
- **Hashing must be portable:** use `shasum -a 256` when present, else `sha256sum`. The script runs under macOS `/bin/bash` 3.2 with BSD tools (R-INFRA-3) and under GNU tools in the devcontainer.

Then commit this repo's own `.claude/managed-file-drift.accept`, with the two lines produced by the `accept` subcommand for `CLAUDE.md` and `.git/hooks/post-commit`.

## Out of scope

- ralph-init Upgrade U2/U4 reading the acceptance list. U2 keeps its own per-file diff and confirm flow.
- Creating the accept file for other projects, or changing the managed table or its rules.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 managed-file-drift.sh check does not report a managed path listed in <project>/.claude/managed-file-drift.accept whose template and project hashes both match the current content — verified by tests/python/test_managed_file_drift.py
- [x] #2 Changing the template content, or changing the project content, of an accepted path makes check report it as outdated again — verified by two tests
- [x] #3 For CLAUDE.md, an edit below '## Project-Specific' leaves an acceptance valid and an edit above it voids it — verified by tests
- [x] #4 managed-file-drift.sh accept <project-dir> <path> prints the accept line for a drifting managed path and exits 2 with a reason for an unmanaged or non-drifting path; it never writes the accept file — verified by tests
- [x] #5 A malformed accept-file line makes check exit 2 with a message naming the file and line number — verified by a test
- [x] #6 This repo commits .claude/managed-file-drift.accept with lines for CLAUDE.md and .git/hooks/post-commit, and bash plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh check . exits 0 with no output; the output is recorded in the task notes
- [x] #7 README.md or the ralph-run SKILL.md preflight section documents the accept file, its line format and the accept subcommand
- [x] #8 On the macOS host, tests/python/test_managed_file_drift.py passes with /bin/bash 3.2 and /usr/bin sed, grep, awk and shasum first on PATH; the output is recorded in the task notes
- [x] #9 uv run ruff check . is clean, uv run pytest passes and LC_ALL=C node_modules/.bin/bats tests/unit passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: managed-file-drift.sh — split compare() into state() + acceptance lookup; add sha256 (shasum -a 256, else sha256sum), digest (rule-scoped bytes: above:<h> hashes only lines above the heading), load_accepted (validates '<path> template=<64hex> project=<64hex>', exits 2 naming file:line), lookup (managed path -> template|rule incl. per-hook rows) and the accept subcommand (prints only; exit 2 for unmanaged/missing/current). Commit .claude/managed-file-drift.accept for CLAUDE.md + .git/hooks/post-commit, un-ignore it in .gitignore (.claude/* is ignored). Tests in tests/python/test_managed_file_drift.py; docs in ralph-run SKILL.md preflight section.

Commit: `57ed5d5` - task-275: let the managed-file drift check accept reviewed differences by content hash

AC #6 container run: 'bash plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh check .' -> rc=1, stdout '.claude/settings.local.json: outdated' only (without the accept file it also lists CLAUDE.md and .git/hooks/post-commit). The remaining line is the devcontainer environment: /workspace/.claude/settings.local.json is a virtiofs mount of templates/devcontainer/container-settings.local.json (byte-identical), by design, not the host's file. AC #6's 'exits 0 with no output' is DEFERRED to the macOS host together with AC #8. Host commands: bash plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh check . ; echo rc=$? — and PATH=/usr/bin:/bin:$PATH uv run pytest tests/python/test_managed_file_drift.py. Record both outputs here and check AC #6 and #8.
Gates (container): ruff clean; pytest 892 passed, 3 skipped; LC_ALL=C bats 153/154 — not ok 140 (R11 settings.local.json shape) is the same container-mount baseline failure seen on master in TASK-274.
Scope note: added '!.claude/managed-file-drift.accept' to this repo's .gitignore (it ignores .claude/*); the ralph-init .gitignore template is unchanged (out of scope) and the ralph-run doc tells other projects to add the line.

Review 1 (task-reviewer): CHANGES REQUESTED — AC #9 left unchecked with bats 153/154. Resolved: LC_ALL=C bats tests/unit in a clean detached worktree of task-275 (/tmp/b275, no mounted .claude/settings.local.json) gives 1..154 with no 'not ok'; master's worktree gives the same. Test 140 fails only in /workspace because .claude/settings.local.json there is the container's virtiofs mount. ruff clean, pytest 892 passed / 3 skipped. AC #9 checked.

Review 2 (task-reviewer): APPROVED, no findings. Left In Progress and unmerged on task-275: Done, version bump and merge wait for the AC #6 and AC #8 macOS host runs (commands above).

AC #6 host (macOS): bash plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh check . -> exit 0, no output (also with PATH=/usr/bin:/bin:$PATH, i.e. /bin/bash 3.2 + BSD tools). Control: with .claude/managed-file-drift.accept moved aside it prints 'CLAUDE.md: outdated' and '.git/hooks/post-commit: outdated', exit 1. 'managed-file-drift.sh accept . <path>' on the host (shasum) prints lines byte-identical to the committed ones produced in the container (sha256sum), for both paths. The container-only '.claude/settings.local.json: outdated' line does not occur on the host. AC #8 host: PATH=/usr/bin:/bin:$PATH gives bash=/bin/bash 3.2.57(1)-release, shasum=/usr/bin/shasum (macOS also has /sbin/sha256sum; the script prefers shasum), awk/sed/grep from /usr/bin; uv run pytest tests/python/test_managed_file_drift.py: 63 passed. Host gates after merging master (0.14.1): uv run ruff check . clean; uv run pytest 900 passed, 4 skipped; LC_ALL=C node_modules/.bin/bats tests/unit 154 ok, 0 not ok.

Commit: `a431bc9` - task-275: bump plugin version to 0.14.2 (patch)
<!-- SECTION:NOTES:END -->
