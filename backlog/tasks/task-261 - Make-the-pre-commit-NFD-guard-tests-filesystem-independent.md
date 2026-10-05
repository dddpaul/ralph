---
id: TASK-261
title: Make the pre-commit NFD guard tests filesystem-independent
status: In Progress
assignee: []
created_date: '2026-10-04 18:41'
updated_date: '2026-10-05 08:48'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Two tests in `tests/unit/pre-commit-hook.bats` — "pre-commit: blocks staging NFD form when NFC exists at HEAD" and "pre-commit: blocks staging NFC form when NFD exists at HEAD" — fail on any macOS APFS host and pass only on a normalization-sensitive filesystem such as the devcontainer's ext4. The suite therefore carries two permanent failures on the host, which makes the CLAUDE.md rule "always run build, linter, and tests before committing" impossible to satisfy literally there, and trains everyone to ignore two red lines.

Root cause, proven by probe on the host (not inferred): APFS is normalization-insensitive for lookup, so the NFC and NFD names are the same file. Writing both forms with shell redirects produced one directory entry and one inode — `stat -f %i` returned the same value for both names — and the NFC path read back the NFD content, because the second write overwrote the first. The test's premise, two distinct paths coexisting, cannot be constructed on this filesystem, so the hook has nothing to block and exits 0 while the test asserts 1. The fixture already sets `core.precomposeunicode false`, so this is the filesystem, not git pre-composing.

Not a regression from recent work: the hook and its test last changed on 2026-09-27 in task-246, and TASK-259 / TASK-260 touched neither.

FIX, verified working on this APFS host before filing. The hook never stats the working tree — it reads only the index and HEAD:

```bash
staged=$(git -c core.quotePath=false diff --cached --name-only)
head_paths=$(git -c core.quotePath=false ls-tree -r HEAD --name-only 2>/dev/null) || exit 0
```

so both HEAD and the index can be built by plumbing, with no working-tree file at all, and the collision then reproduces on APFS. This exact sequence was run on the host; the hook printed BLOCKED and exited 1 with zero files on disk and two paths in the index:

```bash
git init -q -b master
git config core.precomposeunicode false
NFC=$(python3 -c 'import unicodedata,sys;sys.stdout.write(unicodedata.normalize("NFC","й.md"))')
NFD=$(python3 -c 'import unicodedata,sys;sys.stdout.write(unicodedata.normalize("NFD","й.md"))')
# HEAD gets the NFC form, purely via plumbing
blob=$(printf nfc | git hash-object -w --stdin)
git update-index --add --cacheinfo 100644,"$blob","$NFC"
tree=$(git write-tree); commit=$(git commit-tree "$tree" -m "add NFC form")
git update-ref refs/heads/master "$commit"
git read-tree HEAD
# stage the NFD form, also with no file on disk
blob2=$(printf nfd | git hash-object -w --stdin)
git update-index --add --cacheinfo 100644,"$blob2","$NFD"
bash "$HOOK"   # -> BLOCKED ... ; exit 1
```

Prefer this over a `setup()` filesystem probe plus `|| skip`. A skip would silence the host but delete coverage on exactly the platform that produces NFD filenames in the first place, which is the whole reason the guard exists. If some case genuinely cannot be expressed through the index, a probe-based skip is the fallback for that case alone — and it must probe the observed behaviour of the actual test directory, since `make_temp_dir` in `tests/helpers/common.bash` lands under BATS_TEST_TMPDIR and the volume is therefore a runtime fact. Never infer from `uname`: a normalization-sensitive volume can be mounted on macOS, and APFS can be reformatted.

Scope and parity, checked: tests are NOT mirrored into the ralph-init templates — the templates directory holds claude, devcontainer, git-hooks, obsidian and root, and a find for *.bats under it returns nothing. R11 template parity does not apply. The guard itself must not change: this task fixes how the test builds its fixture, not the hook.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Both NFD/NFC collision tests pass on a macOS APFS host: LC_ALL=C node_modules/.bin/bats tests/unit/pre-commit-hook.bats reports 0 failures and 0 skipped
- [x] #2 Neither of the two tests creates a working-tree file for the NFC or NFD name — grep over tests/unit/pre-commit-hook.bats finds no shell redirect into $NFC_NAME or $NFD_NAME inside those two test bodies
- [x] #3 Both tests still assert the hook's observable contract: exit status 1 and BLOCKED in the output
- [x] #4 The tests still fail when the guard is broken: temporarily removing the normalization comparison from plugins/ralph/skills/ralph-init/templates/git-hooks/pre-commit makes both tests fail, the mutation is reverted afterwards, and the observed result is recorded in the task notes
- [x] #5 The guard itself is unchanged: git diff master..HEAD -- plugins/ralph/skills/ralph-init/templates/git-hooks/pre-commit is empty
- [ ] #6 Gates: uv run ruff check . is clean, uv run pytest passes, and LC_ALL=C node_modules/.bin/bats tests/unit passes on the host with no failures
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Execution constraint: AC #1 can only be checked on a normalization-insensitive filesystem, i.e. the macOS APFS host. A devcontainer run sits on ext4, where both tests already pass today, so an in-container run would tick AC #1 vacuously and leave the host failure in place. Either implement this interactively on the host, or run it in the container and then verify AC #1 and AC #6 on the host before marking Done. AC #2 (no working-tree file for either name) is the environment-independent half and is checkable anywhere.

Plan: reuse the existing stage_plumbed helper (index-only staging via hash-object + update-index --cacheinfo) in the two NFD/NFC collision tests, so no working-tree file is written for either name. Move the helper to the top of the file next to the name constants. Verify on a normalization-insensitive volume by pointing TMPDIR at the macOS bind mount, plus a mutation check of the guard.

Commit: `78117f9` - task-261: build the NFD/NFC collision fixtures through the index so they hold on normalization-insensitive volumes

Container verification (Linux; /workspace is the macOS bind mount, which collapses NFC/NFD like APFS — probe: writing both names produced 1 dir entry and the NFC path read back 'nfd'):
- Host failure reproduced by proxy: master's pre-commit-hook.bats run with TMPDIR on the bind mount → 'not ok 2' and 'not ok 3' (the two collision tests), all else ok. With this change, same volume: 13/13 ok, 0 skipped (two consecutive runs). On /tmp (ext4): 13/13 ok.
- AC #2: both collision tests now stage via the existing stage_plumbed helper (hash-object + update-index --cacheinfo), moved to the top of the file; no redirect into $NFC_NAME/$NFD_NAME in those bodies (the remaining 'echo > $NFC_NAME' lines belong to the separate same-byte-path modification test).
- AC #4 mutation: replaced the guard's 'if [ "$e" != "$p" ]' with 'if false' → tests 2, 3 (and 11) fail; reverted, git diff of the hook empty.
- Gates (container): ruff clean; pytest 771 passed; bats tests/unit 138 tests, only 'not ok 124 R11: settings.local.json keeps the template's JSON shape', which fails identically on master (local untracked settings.local.json carries an 'attribution' key — environment, not this change).

HOST VERIFICATION STILL OWED (task execution constraint): AC #1 and AC #6 proved only by proxy on the bind mount. On the host: LC_ALL=C node_modules/.bin/bats tests/unit/pre-commit-hook.bats (expect 0 failures, 0 skipped); uv run ruff check .; uv run pytest; LC_ALL=C node_modules/.bin/bats tests/unit.

Review: ralph:task-reviewer APPROVED (0 blocking, 0 minor, score 10); reviewer independently reproduced the proxy results. Reviewer caveat for AC #6: bats test 124 (R11 settings.local.json shape) fails because the git-ignored .claude/settings.local.json on the shared volume carries an 'attribution' key the template lacks — the host run will likely fail it too until that local file is reconciled; unrelated to this diff. Left In Progress and unmerged on branch task-261 per the execution constraint. On the host: run the AC #1/#6 commands, check AC #1/#6, mark Done, then Merge (bump-version --auto will no-op: no shipped plugins/ralph/** file changed).
<!-- SECTION:NOTES:END -->
