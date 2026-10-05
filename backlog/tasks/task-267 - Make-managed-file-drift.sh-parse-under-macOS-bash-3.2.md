---
id: TASK-267
title: Make managed-file-drift.sh parse under macOS bash 3.2
status: Done
assignee: []
created_date: '2026-10-05 08:16'
updated_date: '2026-10-05 09:43'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh` does not parse under macOS's system bash. Measured on this host:

```text
/bin/bash -n managed-file-drift.sh   (GNU bash 3.2.57, arm64-apple-darwin24)
  line 100: syntax error near unexpected token `;;'
  line 100: `      git) [ -d "$project/.git" ] || continue ;;'
/opt/homebrew/bin/bash -n managed-file-drift.sh   (GNU bash 5.3.20)
  OK
```

Cause: a known bash 3.2 parser defect. The script builds its report inside a command substitution, and a case pattern's unbalanced closing parenthesis inside that substitution ends the substitution early in bash 3.2. The offending block:

```bash
report=$(
  table | while IFS='|' read -r path tmpl rule gate; do
    case $gate in
      git) [ -d "$project/.git" ] || continue ;;
      devcontainer) [ -d "$project/.devcontainer" ] || continue ;;
    esac
```

Two standard fixes, either acceptable: write the patterns in the POSIX leading-parenthesis form, which bash 3.2 parses correctly inside a substitution, or move the loop into a function so the substitution contains only the function call.

```bash
      (git) [ -d "$project/.git" ] || continue ;;
      (devcontainer) [ -d "$project/.devcontainer" ] || continue ;;
```

Impact. `plugins/ralph/skills/ralph-run/scripts/ralph/preflight.py` runs the script as a bash argv resolved through PATH, and ralph-init Upgrade's status table runs it too. On a Mac without Homebrew bash first in PATH, both paths get bash 3.2, the script fails to parse, and preflight prints "WARNING: could not check ralph-init managed files" — the drift detector shipped by TASK-264 is dead on the default macOS install. Preflight degrades to a warning by design, so Ralph still runs. This repository's own pytest run on this host resolved bash to 3.2 and failed `plugins/ralph/skills/ralph-run/tests/test_preflight.py::test_managed_file_drift_warns_without_aborting`. A /bin/bash -n sweep over all 33 git-tracked shell scripts found this one file and no other.

Why nothing caught it. Ralph's devcontainer is Linux, whose bash is 5.x, so no in-container check can see a bash-3.2-only parse failure. Project rule R5 in `.claude/task-reviewer-rules.md` covers GNU versus BSD tools such as sed, stat and date, but says nothing about the shell version, so a reviewer applying it had no reason to look. TASK-264's portability AC was ticked from inside the container.

Add a guard so the class cannot recur silently: a test that runs /bin/bash -n over every git-tracked shell script — including the git-hook templates under the ralph-init templates and the live hooks under .claude/hooks — whenever /bin/bash reports major version 3, and skips with an explicit reason otherwise. And extend R5 to name macOS system bash 3.2 as a syntax target alongside the GNU and BSD tool differences it already covers.

Execution constraint. The defect, the regression proof and the guard are only observable where /bin/bash is 3.2, i.e. this macOS host. In the Linux container the guard skips and the unfixed script parses, so AC #1, AC #3's failing-against-master half and AC #5 must be verified on the host. Implement interactively here, or run it in the container and verify those on the host before marking Done.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 /bin/bash -n plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh succeeds on the macOS host, where /bin/bash is GNU bash 3.2
- [x] #2 plugins/ralph/skills/ralph-run/tests/test_preflight.py::test_managed_file_drift_warns_without_aborting passes on the macOS host, with the drift report rather than the could-not-check warning
- [x] #3 A test runs /bin/bash -n over every git-tracked shell script, including the git-hook templates and the live .claude/hooks scripts, when /bin/bash reports major version 3, and skips with an explicit reason otherwise; it fails against master's version of managed-file-drift.sh on this host, with that result recorded in the task notes
- [x] #4 R5 in .claude/task-reviewer-rules.md names macOS system bash 3.2 as a syntax target alongside the GNU and BSD tool differences it already covers
- [x] #5 Gates on the macOS host: uv run ruff check . is clean, uv run pytest passes, and LC_ALL=C node_modules/.bin/bats tests/unit passes with no failures other than pre-commit-hook.bats tests 34 and 35, which TASK-261 tracks
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Scope check at filing: bash embedded in Markdown is clean too. Of 161 bash fences across git-tracked Markdown, 0 fail only under /bin/bash 3.2; 30 fail under both 3.2 and 5.3 because they are placeholder templates (e.g. task-<id>), not code. The task-reviewer loader snippet parses under 3.2. Extending the guard to fences is optional; if done, it must be differential — flag a fence only when bash 5 parses it and 3.2 does not — or the 30 placeholder fences make it permanently red.

Commit: `a7d7f08` - task-267: parse managed-file-drift.sh under bash 3.2 and guard every tracked script with a bash 3.2 syntax check

Commit: `5a7f7a3` - task-267: name macOS system bash 3.2 as a syntax target in R5

Plan: switch the two case patterns in managed-file-drift.sh's report substitution to the POSIX (pattern) form; add tests/python/test_bash32_syntax.py (bash -n over git-tracked *.sh/*.bash + extensionless sh/bash-shebang files when /bin/bash is major 3, explicit skip otherwise; BASH32_SYNTAX_SHELL overrides /bin/bash); extend R5 with a bash 3.2 syntax paragraph.

Container verification (Linux, /bin/bash 5.2): built GNU bash 3.2.57 from the GNU tarball (parser regenerated with bison 3.8.2 from the patched parse.y) at /tmp/bash32. Sweep of 34 tracked scripts with it: only managed-file-drift.sh failed on master (line 100: syntax error near unexpected token ';;'), identical to the host measurement in the description — fidelity check of the build.
- Guard vs master's managed-file-drift.sh: BASH32_SYNTAX_SHELL=/tmp/bash32 → test_tracked_shell_scripts_parse_under_bash32 FAILED with the line-100 error; with the fix → passed. Under the container's /bin/bash 5 it skips: '/bin/bash reports bash major version 5, not 3 (macOS system bash)'.
- AC #2 simulated: with conftest SYS_PATH temporarily prefixed by a dir whose bash is 3.2.57 (uncommitted), test_managed_file_drift_warns_without_aborting FAILED on master with 'WARNING: could not check ralph-init managed files — ... line 100: syntax error' and PASSED with the fix (drift report). tests/python/test_managed_file_drift.py under bash 3.2 in PATH: master 16 failed / fixed all pass.
- Gates (container): ruff clean; uv run pytest 772 passed 1 skipped; with bash 3.2 driving both guard and preflight fixture 773 passed; bats tests/unit 138 tests, only 'not ok 124 R11: settings.local.json keeps the template's JSON shape', which fails identically on master (pre-existing, container-only; tests 34/35 pass here).

HOST VERIFICATION STILL OWED (task execution constraint): AC #1, AC #3's failing-against-master half on real /bin/bash, and AC #5 have been proved against a source-built bash 3.2.57 in the container, not on the macOS host. Re-run on the host: /bin/bash -n plugins/ralph/skills/ralph-init/scripts/managed-file-drift.sh; uv run pytest; LC_ALL=C node_modules/.bin/bats tests/unit.

Review: ralph:task-reviewer APPROVED (0 blocking, 0 minor, score 10), host-only ACs verified by proxy against /tmp/bash32. Left In Progress and unmerged on branch task-267: the task's execution constraint requires the host re-run before Done. On the host: check AC #1/#2/#3/#5 after the re-run, then mark Done and run the Merge step (bump-version --auto will bump: managed-file-drift.sh is shipped).

Host verification (macOS, interactive session after the Ralph run): AC #1 /bin/bash -n managed-file-drift.sh passes under GNU bash 3.2.57 (arm64-apple-darwin24). AC #2 test_managed_file_drift_warns_without_aborting: 1 passed on the host. AC #3 tests/python/test_bash32_syntax.py: 2 passed with the fix; with master's managed-file-drift.sh swapped in it fails with 'line 100: syntax error near unexpected token ;;' on the real /bin/bash, file restored afterwards. AC #5 gates on the host: ruff clean; pytest 771 passed 2 skipped; bats tests/unit 136 ok, only not-ok 34 and 35 (pre-commit NFD/NFC, tracked by TASK-261). Ralph's container proxy against a source-built bash 3.2.57 matched the host on every point.

Commit: `932d7b8` - task-267: bump plugin version to 0.11.1 (patch)
<!-- SECTION:NOTES:END -->
