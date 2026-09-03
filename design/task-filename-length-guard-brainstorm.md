# Task Filename Length Guard

## Architecture decision

Enforce a **125-byte maximum on committed filenames** (basename) and a **100-char maximum on backlog artifact titles**, via a two-layer guard:

1. **Prevention (PreToolUse):** extend the existing `.claude/hooks/naming-guard.sh` with a title-length rule, widened to cover every filename-producing `backlog` command.
2. **Guarantee (pre-commit):** a new `.claude/hooks/filename-length-guard.sh`, called from `.git/hooks/pre-commit`, that scans staged paths and rejects any basename over 125 bytes.

The two numbers are linked: Syncthing replicates this repo to a Linux ecryptfs volume whose per-name limit is ~140–143 bytes. Syncthing writes each file via a temp name `.syncthing.<basename>.tmp` (+15 bytes), so the committed basename must stay ≤125 for the transfer to fit. The 100-char title cap derives from that: the tightest artifact prefix is `decision-9999 - <title>.md` (overhead 19), leaving 106 of title room at a 125 filename budget — 100 is a safe round cap for all artifact types.

**Why the title check is a sound upper bound.** Measured empirically against backlog.md v1.50.1: the title→slug transform never expands. Alphanumerics and dots pass through 1:1, spaces map to single dashes, runs collapse, all other symbols are dropped. So `slug_length ≤ title_length` always — checking the raw title needs no slugify replication and cannot drift when backlog.md changes its algorithm.

## Components / flows

- **`.claude/hooks/naming-guard.sh`** (edit) — add a second rule beside the ASCII check: extracted title > 100 chars → deny JSON. Widen extraction beyond `backlog task create` to also cover `task edit -t` (the rename path, currently unguarded), `doc create`, `decision create`, `draft create`. Same hook, same wiring, same deny-JSON shape.
- **`.claude/hooks/filename-length-guard.sh`** (new) — invoked from pre-commit. `git diff --cached --name-only --diff-filter=ACMR`, measure each **path component** (not just basename) under `LC_ALL=C` (byte count), reject any segment > 125. Failure message names the file, its byte length, the overage, and suggests `backlog task edit <id> -t "<shorter>"` for `backlog/` paths.
- **`.git/hooks/pre-commit`** (edit) — add a block that calls the new script iff `[ -x .claude/hooks/filename-length-guard.sh ]`, else skips (graceful degradation for projects bootstrapped before this change).
- **`ralph-init` templates** — mirror all three files (R11 parity), and update the `ralph-init` SKILL.md in BOTH Init (Step 3.x file list) and Upgrade Mode (U1–U5) so existing projects receive the new script via `ralph upgrade`.
- **One-time rename** of `task-97` (141 → ~112 char filename) via `backlog task edit 97 -t "..."`.

## Scope cuts

- **No config surface.** 125 is hardcoded; long filenames break ecryptfs, Windows MAX_PATH, and tar/zip round-trips universally, so it ships as a defensible default to all Ralph projects, not a per-project knob.
- **No repo-wide Write/Edit interception.** The pre-commit backstop already catches Write-tool files, manual `mv`, and `design/*.md`; a PreToolUse Write matcher would fire on a hot path for no added guarantee.
- **No slugify replication** in the guard — the raw-title upper bound is sound (see above).

## Open questions

- None blocking. Budget (125), scope (all backlog artifacts), distribution (ship via ralph-init), and structure (separate script called by pre-commit) are all locked.

## Hand-off

Next: single ad-hoc task via `ralph-task` (not PRD-shaped — one cohesive deliverable).

## Distilled for ralph-task

**Direction:** Option B — a two-layer filename-length guard: extend `naming-guard.sh` for prevention at title-entry, add a new `filename-length-guard.sh` called by `.git/hooks/pre-commit` as the commit-time guarantee. Plus rename the one existing over-limit task file.

**Locked decisions (with rationale):**
- **125-byte filename cap.** *Rationale:* Syncthing's `.syncthing.<name>.tmp` temp name adds 15 bytes, and the ecryptfs limit on the sync target is ~140–143 bytes, so the committed basename must stay ≤125 for the transfer to fit.
- **100-char title cap.** *Rationale:* tightest artifact overhead is `decision-9999 - <title>.md` (19), leaving 106 at a 125 budget; 100 is a safe round cap covering all artifact types, and the title→slug transform never expands (measured on backlog.md v1.50.1), so the raw title is a sound upper bound needing no slugify replication.
- **Separate `filename-length-guard.sh`, called by pre-commit.** *Rationale:* keeps the length logic tracked, testable, and template-mirrorable rather than inlined into the NFC-check pre-commit body.
- **`--diff-filter=ACMR` in the pre-commit scan.** *Rationale:* an unfiltered `--name-only` includes the staged deletion of the old long path, which would make the `task-97` rename commit block itself.
- **`LC_ALL=C` byte measurement of every path component.** *Rationale:* ecryptfs limits bytes not characters, and a long directory segment breaks sync exactly like a long filename; `${#name}` in a UTF-8 locale under-counts multibyte names.
- **`[ -x ]` guard in pre-commit.** *Rationale:* projects bootstrapped before this change lack the script; skip gracefully instead of hard-failing, matching the existing NFC-check bail-out.
- **Ship to all projects via ralph-init, no config.** *Rationale:* long filenames break ecryptfs/Windows/archive round-trips universally; 125 is a defensible hardcoded default.
- **Single task, ~8 ACs, not split.** *Rationale:* the guard is one deliverable — shipped half-installed (guard without rename) it blocks the first commit touching `task-97`; rollback coherence (rule 4) keeps it together.

**Scope cuts:**
- No config/env knob for the limit.
- No repo-wide Write/Edit PreToolUse interception (pre-commit already covers non-CLI files).
- No slugify replication in the title check.

**Acceptance criteria (sketch):**
- `naming-guard.sh` denies a `backlog task create` whose title > 100 chars; allows ≤100.
- `naming-guard.sh` also applies the length + ASCII checks to `task edit -t`, `doc create`, `decision create`, `draft create` titles.
- `.claude/hooks/filename-length-guard.sh` exists, executable; rejects a staged path with a >125-byte component, allows ≤125.
- Guard uses `--diff-filter=ACMR` (a staged deletion of a long path does not block) and `LC_ALL=C` byte counting; checks each path component.
- `.git/hooks/pre-commit` calls the script iff executable, skips otherwise.
- `task-97` renamed so its filename is ≤125 bytes; no dangling references to the old filename.
- All three files mirrored to `ralph-init` templates (R11 parity), and `ralph-init` SKILL.md updated in BOTH Init (Step 3.x) and Upgrade Mode (U1–U5).
- Tests cover: over/at-limit title deny/allow, over/at-limit basename, staged-deletion allowed, long directory segment rejected, multibyte byte-count. `uv run pytest` and `uv run ruff check .` pass.

**Implementation checklist:**
- Extend `.claude/hooks/naming-guard.sh`: add title>100 deny rule; widen title extraction to `task edit -t`, `doc create`, `decision create`, `draft create`.
- Write `.claude/hooks/filename-length-guard.sh` (staged scan, `--diff-filter=ACMR`, `LC_ALL=C`, per-component, ≤125, actionable message).
- Edit `.git/hooks/pre-commit` to call it behind `[ -x ]`.
- Mirror all three into `plugins/ralph/skills/ralph-init/templates/{claude/hooks,git-hooks}/`.
- Update `ralph-init` SKILL.md Init Step 3.x file list AND Upgrade Mode U1–U5.
- `backlog task edit 97 -t "Fix TASK-96 defects in ralph-review Step 2b: allowlist rule, REPO_ROOT substitution, classify grep"`.
- Add hook tests; run `uv run pytest` + `uv run ruff check .`.
