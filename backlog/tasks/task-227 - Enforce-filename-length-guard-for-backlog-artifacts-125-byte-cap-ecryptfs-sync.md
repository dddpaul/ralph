---
id: TASK-227
title: >-
  Enforce filename-length guard for backlog artifacts (125-byte cap, ecryptfs
  sync)
status: Done
assignee: []
created_date: '2026-09-03 20:13'
updated_date: '2026-09-03 20:47'
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
- [x] #1 naming-guard.sh denies a backlog task create whose title > 100 chars; allows a title of exactly 100 chars
- [x] #2 naming-guard.sh applies both the length and ASCII checks to task edit -t, doc create, decision create, and draft create titles
- [x] #3 .claude/hooks/filename-length-guard.sh exists and is executable; it rejects a staged path with any component > 125 bytes and allows one at exactly 125 bytes
- [x] #4 The guard uses git diff --cached --name-only --diff-filter=ACMR (a staged deletion of a long path does not block) and measures every path component under LC_ALL=C (byte count)
- [x] #5 .git/hooks/pre-commit calls the guard script iff it is executable, and skips silently otherwise
- [x] #6 task-97 is renamed so its filename is <=125 bytes, with no dangling references to the old filename anywhere in the repo
- [x] #7 All three files (naming-guard.sh, filename-length-guard.sh, pre-commit) are mirrored to plugins/ralph/skills/ralph-init/templates/, and ralph-init SKILL.md is updated in BOTH Init (Step 3.x) and Upgrade Mode (U1-U5)
- [x] #8 Tests cover over/at-limit title deny-allow, over/at-limit basename, staged-deletion allowed, long directory segment rejected, and multibyte byte-count; uv run pytest and uv run ruff check . both pass
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: (1) extend .claude/hooks/naming-guard.sh — add >100-char title deny plus widened title extraction for `task create`, `task edit -t/--title`, `doc create`, `decision create`, `draft create`; (2) new .claude/hooks/filename-length-guard.sh — scan `git diff --cached --name-only --diff-filter=ACMR`, measure every path component under LC_ALL=C, reject >125 bytes with an actionable message; (3) .git/hooks/pre-commit calls it behind `[ -x ]`; (4) register naming-guard in .claude/settings.json for the four newly-covered backlog commands (without this the widened extraction is dead code); (5) mirror naming-guard.sh, filename-length-guard.sh, settings.json and pre-commit into plugins/ralph/skills/ralph-init/templates/ (R11); (6) update ralph-init SKILL.md Init 3.3/3.7a/Step-4 summary and Upgrade U2/U3/U4/U5; (7) rename task-97 via `backlog task edit 97 -t`; (8) add bats coverage in tests/unit/pretools-hooks.bats + new tests/unit/filename-length-guard.bats; run bats, `uv run pytest`, `uv run ruff check .`. Baseline captured: 66/66 bats unit tests and 346 pytest tests green on master.

Commit: `b7ed79b` - task-227: enforce a 125-byte filename cap via naming-guard title rule and a pre-commit filename-length guard

Implementation notes (TASK-227):

- **naming-guard.sh** now carries two rules. The ASCII rule runs first (so the length check only ever sees ASCII and `${#target}` equals the byte count), then a 100-char title cap. Title extraction was widened to `task|doc|decision|draft create` and to `task edit --title` / `task edit -t`. The `-t` form is anchored on a preceding whitespace so `--type` and `--title` cannot match it. Because `sed -n ...p` emits one line per match and a single Bash tool call can carry several commands, each extracted name is validated separately rather than as a concatenation.
- **Branch names keep the ASCII rule but are exempt from the length cap** — they produce no artifact filename. Covered by a test.
- **.claude/settings.json (+ template)** gained four `if:` registrations (`backlog task edit`, `backlog doc create`, `backlog decision create`, `backlog draft create`) pointing at naming-guard.sh. Without them the widened extraction in AC #2 would never fire — the hook is only invoked for commands settings.json routes to it. Not in the task checklist, but AC #2 is unsatisfiable without it.
- **filename-length-guard.sh** exports `LC_ALL=C` at the top so `${#comp}` counts bytes, and walks each path component with pure POSIX parameter expansion (no arrays, no `grep -P`, no GNU-only flags) for R5 portability. It reads `git -c core.quotePath=false diff --cached --name-only --diff-filter=ACMR`; `core.quotePath=false` matters as much as the byte counting, since C-style `\\320\\271` escapes would inflate a multibyte name fourfold.
- **Deviation 1 — `backlog task edit -t` does NOT rename the file.** The task checklist assumed it does. Verified against backlog.md v1.51.0: the title in frontmatter changes, the filename does not (this is also why task-215's filename still carried a pre-rename slug). AC #6 therefore needed an explicit `git mv` on top of the title edit. The new basename was taken from a probe of backlog's own slugifier in a scratch project, so it matches what backlog would have generated.
- **Deviation 2 — there were THREE over-limit task files, not one.** The task body says "the one existing over-limit task file"; `task-97` (141 B), `task-95` (132 B) and `task-215` (129 B) all exceeded 125. Shipping the guard while leaving two known violations behind would reproduce exactly the half-installed failure the task's own rationale warns about, so all three were brought under the cap:
  - task-97 -> title shortened to the string the task prescribes (98 chars) + `git mv`; filename now 108 B.
  - task-95 -> **title preserved verbatim** (a Done task's record; R14 spirit) and only the filename shortened, to 69 B.
  - task-215 -> title already compliant (81 chars); only its stale filename was moved onto the current title's slug, 91 B.
  A repo-wide sweep of `git ls-files` now reports zero path components over 125 bytes.
- **Verified end-to-end through the live hook, not only in bats:** the implementation commit itself stages the deletion of all three long paths and passed (proving the `--diff-filter=ACMR` decision), and a deliberate 126-byte staged path was rejected by `.git/hooks/pre-commit` with the actionable message and left HEAD unchanged.
- **Gates:** bats unit 95/95, integration 52/52, e2e 6/6; `uv run pytest` 346 passed; `uv run ruff check .` clean. (`completion-signal.bats` test 1 flaked once under concurrent load and passed in isolation and on re-run of the full suite.)

Commit: `4018f05` - task-227: re-mirror naming-guard.sh so the ralph-init template matches the live per-command check

Review round 1 (task-reviewer): CHANGES REQUESTED — one blocker. `templates/claude/hooks/naming-guard.sh` had been mirrored from an intermediate version, before the per-command loop landed, so the template shipped a copy that fails this repo's own `pretools-hooks.bats` test 41 and would have been offered as an 'upgrade' over the correct live file by ralph-init U2/U4. Fixed by re-mirroring (commit `4018f05`); all four R11 pairs now diff silent, the template copy passes all 46 pretools tests when swapped in for the live one, and the unit suite is 95/95. The reviewer's non-blocking note — that no automated test pins the R11 parity table, which is why the drift shipped — is filed as TASK-228.

Review round 2 (task-reviewer): APPROVED. Verified the fix at blob level — `.claude/hooks/naming-guard.sh` and its ralph-init template are now the same git object (`c87389b`), differing only in the exec bit, which matches the sibling convention (every template `*-guard.sh` is 644; ralph-init Step 3.7a does the chmod). Swap-in test 46/46, unit suite 95/95, pytest 346 passed, ruff clean, integration 52/52, e2e 6/6. All 8 ACs genuinely satisfied. Follow-up TASK-228 (automated R11 parity test) deliberately kept out of this branch.

Commit: `a65b6f8` - task-227: bump plugin version to 0.4.0 (minor)
<!-- SECTION:NOTES:END -->
