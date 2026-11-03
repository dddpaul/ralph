---
id: TASK-294
title: >-
  Make the shipped git pre-commit hook run under macOS bash 3.2 by dropping
  declare -A
status: Done
assignee: []
created_date: '2026-11-03T19:02:00Z'
updated_date: '2026-11-03T21:21:00Z'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

The git pre-commit hook that ralph-init ships (`plugins/ralph/skills/ralph-init/templates/git-hooks/pre-commit`, installed as `.git/hooks/pre-commit`) runs under `#!/usr/bin/env bash` and uses an associative array, `declare -A head_by_nfc` at line 70, added by TASK-136. Bash 3.2, which macOS ships as `/bin/bash`, has no associative arrays: `declare -A` fails with `declare: -A: invalid option`, `set -euo pipefail` aborts the hook with exit 2, and git aborts the commit.

So on any Mac where `bash` on PATH is `/bin/bash`, every commit in a Ralph project with at least one file in HEAD is rejected. That includes a Mac without Homebrew bash, git run from a GUI client or IDE (PATH `/usr/bin:/bin:/usr/sbin:/sbin`), and a shell that puts `/bin` first. The owner's Mac only escapes it because Homebrew's bash comes first on PATH.

Found during TASK-291's host check. Reproduced on macOS: in a scratch repo with one commit and a newly staged file, `bash <hook>` gives rc 2 and the declare error when `bash` is `/bin/bash` 3.2.57, and rc 0 when it is Homebrew bash 5.3. With /usr/bin first on PATH, `LC_ALL=C bats tests/unit` fails cases 44-46, 49, 54 and 55 (all in `tests/unit/pre-commit-hook.bats`). Run that check outside the Claude Code sandbox, where Apple's python3 shim and diff fail on 'Operation not permitted'.

`tests/python/test_bash32_syntax.py` (TASK-267) did not catch it: it runs `bash -n`, and `declare -A` is a run-time error, not a parse error.

## Fix

Replace the associative array with a bash 3.2 construct, for example "nfc<TAB>path" lines in a string, keeping the NFC/NFD behaviour exactly. Read the lookup key through ENVIRON, not `awk -v`, because `-v` processes backslash escapes and would mangle a path that contains a backslash:

```bash
# bash 3.2 (macOS /bin/bash) has no associative arrays: index HEAD as "nfc<TAB>path" lines.
head_index=""
while IFS= read -r p; do
  [ -z "$p" ] && continue
  head_index+="$(to_nfc "$p")"$'\t'"$p"$'\n'
done <<< "$head_paths"
# ... per staged path:
existing=$(printf '%s' "$head_index" | NFC_KEY="$nfc" awk -F'\t' '$1 == ENVIRON["NFC_KEY"] { print $2 }')
```

Also add a static guard, because `bash -n` cannot see these constructs. A pytest case should fail when any git-tracked shell script uses `declare -A`, `local -A`, `typeset -A`, `mapfile` or `readarray` outside a comment. Today only this hook does. Do not include `|&` or `&>>`: the commit guards' jq lexer program contains those characters as data.

No new Upgrade step is needed. Git hooks are ralph-init managed files: `managed-file-drift.sh` reports an old copy as outdated, and Upgrade U4 overwrites it.

## Scope

Out of scope:
- the hook's per-path normalizer calls (performance);
- the filename-length guard part of the hook;
- other scripts, unless the new static guard finds one.

## Files

- `plugins/ralph/skills/ralph-init/templates/git-hooks/pre-commit` (exists)
- `.git/hooks/pre-commit`: this repo's installed copy, kept byte-identical (not tracked)
- `tests/unit/pre-commit-hook.bats` (exists)
- `tests/python/test_bash32_syntax.py` (exists): extend it, or add a sibling
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 plugins/ralph/skills/ralph-init/templates/git-hooks/pre-commit uses no declare -A, local -A, typeset -A, mapfile or readarray, and .git/hooks/pre-commit is byte-identical to the template
- [x] #2 A pytest case fails when any git-tracked shell script uses declare -A, local -A, typeset -A, mapfile or readarray outside a comment, and passes on the fixed tree
- [x] #3 The NFC/NFD behaviour is unchanged: every existing case in tests/unit/pre-commit-hook.bats passes, plus a new case where a HEAD path containing a backslash still blocks its NFD duplicate
- [x] #4 LC_ALL=C bats tests/unit, uv run pytest and uv run ruff check . pass
- [x] #5 On the macOS host, outside the sandbox: PATH="/usr/bin:/bin:/opt/homebrew/bin:$PATH" LC_ALL=C bats tests/unit/pre-commit-hook.bats has no failures, and a commit in a scratch repo with the hook installed and /bin/bash first on PATH succeeds; both results are recorded in the task notes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan: replace declare -A in the pre-commit template with a nfc<TAB>path string index looked up via awk ENVIRON; copy to .git/hooks; add a static pytest guard in test_bash32_syntax.py for declare/local/typeset -A, mapfile, readarray outside comments; add a bats case for a backslash HEAD path.

Commit: `c03f563` - task-294: index HEAD paths without associative arrays in the pre-commit hook and statically reject bash 4 builtins

Commit: `d4341fa` - task-294: restore the executable bit on the pre-commit hook template

AC5 DEFERRED to the macOS host outside the Claude Code sandbox: this Linux container has no /bin/bash 3.2. Follow-up on the host: run PATH="/usr/bin:/bin:/opt/homebrew/bin:$PATH" LC_ALL=C bats tests/unit/pre-commit-hook.bats and a scratch-repo commit with the hook installed and /bin/bash first on PATH; record both results here. Known limitation (reviewer, minor): the static guard strips from any whitespace-preceded # even inside quotes, so 'echo "a # b"; declare -A x' would be missed; no tracked script does this.

Replaced declare -A in the pre-commit template with an nfc<TAB>path string index; the lookup goes through awk ENVIRON (backslash-safe) with a forced string compare. Installed copy .git/hooks/pre-commit is byte-identical. Added a static pytest guard (test_bash32_syntax.py) for declare/local/typeset -A, mapfile and readarray outside comments, plus two bats cases (backslash HEAD path; numeric-lookalike paths). Both cases are mutation-checked. Final: pytest 1028 passed / 3 skipped, ruff clean, bats tests/unit 204/205 (the R11 settings.local.json failure comes from the gitignored local file and also fails on master). task-reviewer APPROVED on re-review. AC5 deferred to the macOS host (see above).

Commit: `1b9cb61` - task-294: bump plugin version to 0.14.15 (patch)

macOS host verification (after merge, master 0.14.15), outside the sandbox with PATH=/usr/bin:/bin:/opt/homebrew/bin:$PATH, which gives bash 3.2.57, Apple git 2.50.1 and python3 3.9.6. LC_ALL=C bats tests/unit/pre-commit-hook.bats: 15/15, and the full LC_ALL=C bats tests/unit under the same PATH: 205/205. Before the fix this PATH failed cases 44-46, 49, 54 and 55. Real commits: a scratch repo with the template hook installed as .git/hooks/pre-commit, with env bash resolving to /bin/bash 3.2.57, accepted the first commit and then a second commit with HEAD present, which runs the NFC check (2 commits in log). Host gates on master: ruff clean, uv run pytest 1027 passed / 4 skipped, LC_ALL=C bats tests/unit 205/205.
<!-- SECTION:NOTES:END -->
