---
id: TASK-227
title: >-
  Enforce filename-length guard for backlog artifacts (125-byte cap, ecryptfs
  sync)
status: In Progress
assignee: []
created_date: '2026-09-03 20:13'
updated_date: '2026-09-03 20:20'
labels:
  - 'feature:task-filename-length-guard'
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Direction:** Option B — a two-layer filename-length guard: extend `naming-guard.sh` for prevention at title-entry, add a new `filename-length-guard.sh` called by `.git/hooks/pre-commit` as the commit-time guarantee. Plus rename the one existing over-limit task file.

**Locked decisions (with rationale):**
- **125-byte filename cap.** *Rationale:* Syncthing's `.syncthing.<name>.tmp` temp name adds 15 bytes, and the ecryptfs limit on the sync target is ~140-143 bytes, so the committed basename must stay <=125 for the transfer to fit.
- **100-char title cap.** *Rationale:* tightest artifact overhead is `decision-9999 - <title>.md` (19), leaving 106 at a 125 budget; 100 is a safe round cap covering all artifact types, and the title->slug transform never expands (measured on backlog.md v1.50.1), so the raw title is a sound upper bound needing no slugify replication.
- **Separate `filename-length-guard.sh`, called by pre-commit.** *Rationale:* keeps the length logic tracked, testable, and template-mirrorable rather than inlined into the NFC-check pre-commit body.
- **`--diff-filter=ACMR` in the pre-commit scan.** *Rationale:* an unfiltered `--name-only` includes the staged deletion of the old long path, which would make the `task-97` rename commit block itself.
- **`LC_ALL=C` byte measurement of every path component.** *Rationale:* ecryptfs limits bytes not characters, and a long directory segment breaks sync exactly like a long filename; `${#name}` in a UTF-8 locale under-counts multibyte names.
- **`[ -x ]` guard in pre-commit.** *Rationale:* projects bootstrapped before this change lack the script; skip gracefully instead of hard-failing, matching the existing NFC-check bail-out.
- **Ship to all projects via ralph-init, no config.** *Rationale:* long filenames break ecryptfs/Windows/archive round-trips universally; 125 is a defensible hardcoded default.
- **Single task, ~8 ACs, not split.** *Rationale:* the guard is one deliverable — shipped half-installed (guard without rename) it blocks the first commit touching `task-97`; rollback coherence keeps it together.

**Scope cuts:**
- No config/env knob for the limit.
- No repo-wide Write/Edit PreToolUse interception (pre-commit already covers non-CLI files).
- No slugify replication in the title check.

**Implementation checklist:**
- Extend `.claude/hooks/naming-guard.sh`: add title>100 deny rule; widen title extraction to `task edit -t`, `doc create`, `decision create`, `draft create`.
- Write `.claude/hooks/filename-length-guard.sh` (staged scan, `--diff-filter=ACMR`, `LC_ALL=C`, per-component, <=125, actionable message).
- Edit `.git/hooks/pre-commit` to call it behind `[ -x ]`.
- Mirror all three into `plugins/ralph/skills/ralph-init/templates/{claude/hooks,git-hooks}/`.
- Update `ralph-init` SKILL.md Init Step 3.x file list AND Upgrade Mode U1-U5.
- Rename task-97 via: backlog task edit 97 -t "Fix TASK-96 defects in ralph-review Step 2b: allowlist rule, REPO_ROOT substitution, classify grep"
- Add hook tests; run `uv run pytest` + `uv run ruff check .`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 naming-guard.sh denies a backlog task create whose title > 100 chars; allows a title of exactly 100 chars
- [ ] #2 naming-guard.sh applies both the length and ASCII checks to task edit -t, doc create, decision create, and draft create titles
- [ ] #3 .claude/hooks/filename-length-guard.sh exists and is executable; it rejects a staged path with any component > 125 bytes and allows one at exactly 125 bytes
- [ ] #4 The guard uses git diff --cached --name-only --diff-filter=ACMR (a staged deletion of a long path does not block) and measures every path component under LC_ALL=C (byte count)
- [ ] #5 .git/hooks/pre-commit calls the guard script iff it is executable, and skips silently otherwise
- [ ] #6 task-97 is renamed so its filename is <=125 bytes, with no dangling references to the old filename anywhere in the repo
- [ ] #7 All three files (naming-guard.sh, filename-length-guard.sh, pre-commit) are mirrored to plugins/ralph/skills/ralph-init/templates/, and ralph-init SKILL.md is updated in BOTH Init (Step 3.x) and Upgrade Mode (U1-U5)
- [ ] #8 Tests cover over/at-limit title deny-allow, over/at-limit basename, staged-deletion allowed, long directory segment rejected, and multibyte byte-count; uv run pytest and uv run ruff check . both pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) extend .claude/hooks/naming-guard.sh — add >100-char title deny plus widened title extraction for `task create`, `task edit -t/--title`, `doc create`, `decision create`, `draft create`; (2) new .claude/hooks/filename-length-guard.sh — scan `git diff --cached --name-only --diff-filter=ACMR`, measure every path component under LC_ALL=C, reject >125 bytes with an actionable message; (3) .git/hooks/pre-commit calls it behind `[ -x ]`; (4) register naming-guard in .claude/settings.json for the four newly-covered backlog commands (without this the widened extraction is dead code); (5) mirror naming-guard.sh, filename-length-guard.sh, settings.json and pre-commit into plugins/ralph/skills/ralph-init/templates/ (R11); (6) update ralph-init SKILL.md Init 3.3/3.7a/Step-4 summary and Upgrade U2/U3/U4/U5; (7) rename task-97 via `backlog task edit 97 -t`; (8) add bats coverage in tests/unit/pretools-hooks.bats + new tests/unit/filename-length-guard.bats; run bats, `uv run pytest`, `uv run ruff check .`. Baseline captured: 66/66 bats unit tests and 346 pytest tests green on master.
<!-- SECTION:NOTES:END -->
