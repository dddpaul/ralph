---
id: TASK-281
title: Fix two PreToolUse hook guard templates that deny unrelated Bash commands
status: Done
assignee: []
created_date: '2026-10-29T07:03:00Z'
updated_date: '2026-11-03 16:43'
labels:
  - 'feature:ralph-init'
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

Two PreToolUse hook guards shipped by ralph-init deny Bash commands they were never registered for. Because they are shipped templates, the defect reaches every project ralph-init touches, and a consuming project cannot fix it locally: U4 overwrites `.claude/hooks/*-guard.sh` on upgrade and `managed-file-drift.sh` flags any local edit as drift on every ralph-run preflight. Observed repeatedly in a consuming project where it blocked `backlog task create`, `backlog task edit --append-notes` and a `python3` heredoc, and made the trailer policy impossible to document through the backlog CLI at all.

Throughout this task `G<SP>C` stands for the two-word phrase "git" and "commit" separated by a space. The literal is elided on purpose: `commit-prefix-guard.sh` denies any command whose text contains it, which is defect 2, and spelling it out makes this task file unwritable through the CLI. That is the clearest available demonstration of the bug.

## Why the two earlier fixes did not cover this

- **TASK-123 (Done)** added the gate `case "$cmd" in *"G<SP>C"*) ;; *) exit 0;; esac` to `commit-prefix-guard.sh`, which is now line 10. It correctly stopped a non-commit command such as `kill 1` from firing the guard. But a free substring test also matches any command that merely *mentions* the phrase, and TASK-123 did not touch the message extraction. So the guard moved from one false-positive class to another. TASK-123's own AC5 asked for a decision on whether the `settings.json` `if:` directive is real filtering or documentation only - that question is still open and is now load-bearing (see AC below).
- **TASK-134 (Done)** fixed `templates/git-hooks/commit-msg`, the **git** hook, by stripping the scissor section. That is a different file from the Claude Code PreToolUse guard `templates/claude/hooks/commit-msg-guard.sh`, whose unconditional grep has never been addressed.

## Defect 1 - commit-msg-guard.sh has no self-gate at all

The script greps the entire `tool_input.command` with nothing narrowing it: the file contains **zero** `case` statements, despite a header comment naming the commit and pull-request-create triggers. Any Bash command whose text contains the forbidden trailer names is denied, whatever the command is.

Relevant: the consuming project registers this script with `if:` conditions for only those two triggers, yet it ran on commands matching neither. Either `if:` does not filter PreToolUse hooks, or it was not applied. Since the sibling guards rely on `if:`, this needs settling rather than assuming.

## Defect 2 - commit-prefix-guard.sh cannot parse a multi-line message

Line 18 is `msg=$(echo "$cmd" | sed -n 's/.*-m[[:space:]]*"\(.*\)".*/\1/p')`. `sed` is line-based, so a message whose opening and closing quotes sit on different lines never matches. The single-quote fallback at line 20 and the heredoc fallback at line 23 miss too, `msg` ends up empty, and the final `grep -qE "^task-N: "` fails on the empty string - so a **correctly prefixed** multi-line message is denied. Reproduced in the consuming project: the identical message was denied as multi-line and accepted when flattened to one line. Combined with line 10's substring gate, a `backlog task edit --append-notes` whose notes quoted that pattern was also denied - exactly the case the comment on line 9 claims to prevent.

## Scope

In scope:
- Gate both guards so `git` is the program and `commit` its subcommand at a command position (start of string, or after `;`, `&&`, `||`, `|` or a newline) rather than a substring anywhere in the text.
- Replace the line-based message extraction with something not line-bound: read the whole command into a variable and match with bash pattern matching (bash 3.2) and `jq`, handling `-m` with multi-line double and single quotes, `--message=`, `-F`/`--file` (read the named file), and heredoc, including `cat <<'MSG' | G<SP>C -F -`, the form this repo uses for multi-line messages. No `python3`: no shipped hook depends on it today, a consuming project may not have it, and a guard whose interpreter is missing errors out and stops enforcing.
- When the command is a real commit but no message can be extracted, prefer allowing over denying, and record that trade-off in the notes - a false deny blocks legitimate work, which is the whole complaint.
- Keep the repo's own `.claude/hooks/` copies in step with the templates.

Out of scope:
- Changing either policy. The trailer ban and the task-prefix rule both stay and must still fire on real commits.
- `templates/git-hooks/commit-msg`, already handled by TASK-134.
- Repairing this repo's duplicate task IDs, which blocks ID-based backlog commands here - see the note at the end.

## Files

- `plugins/ralph/skills/ralph-init/templates/claude/hooks/commit-msg-guard.sh` (exists) - add the missing gate; currently an unconditional grep.
- `plugins/ralph/skills/ralph-init/templates/claude/hooks/commit-prefix-guard.sh` (exists) - fix the gate on line 10 and the extraction on lines 18-23.
- `.claude/hooks/commit-msg-guard.sh` (exists) - this repo's own copy, keep byte-identical to the template.
- `.claude/hooks/commit-prefix-guard.sh` (exists) - same.
- `tests/unit/pretools-hooks.bats` (exists) - add regression cases next to the existing guard cases (bats, as TASK-134 did for the git hook; `uv run pytest` does not run bats).

## Source

Source: /home/paul/src/mycloud@a7366223529e

## Before starting (destination Claude validation checklist)

Before running this task, verify:
1. All `(exists)` file paths in the Files section still exist in this repo.
2. Each AC is objectively pass/fail (a grep, test invocation, build command, or visible behavior - not "works correctly").
3. All dependencies in the task's frontmatter are status=Done.
4. Out-of-scope items are not accidentally pulled in by ambiguous AC.

If anything is unclear or any check fails: STOP and ask the user. Do NOT start work blindly.

## Note on this repo's backlog state

`backlog task list --plain` exits 1 here with "4 duplicate task ID groups affect 9 files" - TASK-77, TASK-101, TASK-102 and TASK-235 each exist in both `backlog/tasks/` and `backlog/archive/tasks/`, and the CLI says ID-based commands are blocked until repaired. This task was created anyway because creation is not ID-based and the highest existing id is 280, so no new collision was introduced. But `backlog task view <this id>` and `backlog task edit <this id>` may refuse until the collision is fixed; `backlog doctor` previews the repair. Worth its own task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 commit-msg-guard.sh exits 0 silently with no output for a command that is not a real commit or pull-request-create, verified by piping a tool_input whose command is a backlog task create carrying the forbidden trailer names in its text
- [x] #2 commit-msg-guard.sh still emits the deny JSON for a real commit whose message contains a forbidden trailer, and for one containing the forbidden heading
- [x] #3 commit-prefix-guard.sh exits 0 silently on a task-N branch for a correctly prefixed message whose -m value spans several lines
- [x] #4 commit-prefix-guard.sh still emits the deny JSON on a task-N branch for an unprefixed and for a wrongly prefixed message, tested both as a single line and as multiple lines
- [x] #5 commit-prefix-guard.sh exits 0 silently for a command that merely mentions the two-word git-commit phrase without being a commit, such as a backlog task edit whose notes quote that pattern
- [x] #6 Message extraction, in bash and jq only (no python3), handles -m with multi-line double quotes, -m with multi-line single quotes, --message=, -F and --file reading the named file, and a heredoc, including cat <<'MSG' | G<SP>C -F -; the chosen behaviour when no message can be extracted is recorded in the task notes with its rationale
- [x] #7 Regression cases in tests/unit/pretools-hooks.bats cover each case above and pass under LC_ALL=C bats tests/unit, uv run pytest still passes, and this repo's .claude/hooks copies of both scripts are byte-identical to the templates
- [x] #8 Both scripts pass bash -n and satisfy R-INFRA-3 GNU and BSD userland plus bash 3.2 portability
- [x] #9 The notes settle TASK-123's open AC5 question with evidence from a controlled run: a throwaway project whose logging PreToolUse hook carries if: Bash(G<SP>C *), and a nested claude -p that runs a plain command, a command quoting the two-word phrase, and a multi-line heredoc mentioning it; the notes record which of the three fired the hook. If the container cannot run it, the notes say why and leave it for the macOS host
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Handoff gate (destination): yellow, clarified with the user. Y1 - the existing guard tests are bats in tests/unit/pretools-hooks.bats, which uv run pytest never runs; AC #7 now names that file and LC_ALL=C bats tests/unit. Y2 - extraction is limited to bash and jq: no shipped hook uses python3, a consuming project may not have it, and a guard whose interpreter is missing stops enforcing (description and AC #6). Y3 - AC #6 names cat <<'MSG' | G<SP>C -F -, the form this repo uses for multi-line messages. Y4 - the if: question moved out of AC #8 into new AC #9 with a defined controlled run (throwaway project, logging hook, nested claude -p over three commands); if the container cannot run it, it is left for the macOS host. Not changed: the gate is line 11, not 10; the duplicate-ID note is stale (backlog task list exits 0).

Plan: replace the substring gate and the sed extraction in both guards with one jq lexer (embedded identically in both scripts, pinned equal by a bats case) that splits the command into simple commands outside quotes and heredoc bodies, does quote removal, attaches heredoc bodies, and recognises git [global opts] commit / gh pr create at command position. commit-prefix-guard reads -m/--message/-F/--file/heredoc stdin from the parsed commit words; commit-msg-guard keeps its whole-command grep but only after the gate. Add bats regressions; mirror to .claude/hooks; run the if: probe for AC9 if the container can.

No-message behaviour (AC6): when the command is a real commit but no message can be extracted (--amend --no-edit, -C/--reuse-message, --fixup, -F naming a missing or unreadable file, -F - with no heredoc in sight, an editor commit), commit-prefix-guard allows it. A false deny blocks legitimate work, which is the defect this task fixes, while a missed prefix only costs a cosmetic rename; a deny on an unparsed form would rebuild the old bug for every form the lexer does not know. The prefix is checked on the subject (first non-blank line), which is what 'must start with' means; the old grep accepted task-N: on any line.

Design: one jq lexer (bash 3.2 + jq 1.6, no python3/awk) is embedded byte-identically in both guards between '# >>> shared command lexer' markers; a bats case pins the two blocks equal. It splits the command into simple commands on ; && || | & ( ) and newline outside quotes, comments and heredoc bodies, removes quotes (single, double with escapes, $'...', backslash), attaches heredoc bodies (<<, <<-, quoted or bare delimiter) to their command, and special-cases -m "$(cat <<'EOF' ... EOF)". A command is a commit when, after leading VAR=value words, the program is git (or a path ending in /git) and, past git's own options (-C/-c/--git-dir/--work-tree/--namespace/--config-env take an argument), the subcommand is commit; gh pr create likewise. jq regexes run anchored on the remaining string, so a 60 KB heredoc command lexes in ~0.3 s, where a bash char loop was quadratic (13 s at 90 KB). A cheap substring prefilter still exits before jq for every command that cannot be a commit. commit-msg-guard keeps its whole-command grep, but only once the gate says a real commit or pr create is present, so the trailer policy is unchanged for real commits.

Dogfooding: the old prefix guard denied two of this session's own probe commands that only mentioned the phrase, once inside a quoted shell-function argument and once in a heredoc body piped to a file, which is the reported defect reproduced live.

AC8: bash -n passes on both scripts (bash 5.2 here). No bash 3.2 binary exists in the container, so 3.2 parsing is by inspection against R-INFRA-3: no case pattern inside $( ), no heredoc inside $( ) (the lexer is loaded with read -r -d '' <<'JQ'), no declare -A / mapfile / ${v,,} / |& / &>>; arrays use items+=( ) (bash 3.1+), $'\n' and $(<file) are 3.x builtins. Userland calls are cat, jq, grep -qE/-qiE/-oE, sed 's/…//', git, all GNU/BSD-common. Host check left: /bin/bash -n on both scripts on macOS.

AC9 (TASK-123 AC5, does if: filter PreToolUse hooks): the controlled run cannot happen in this container. claude 2.1.283 is installed but not logged in, so a nested claude -p only prints 'Not logged in · Please run /login' and runs no tools, and no hook can fire. Left for the macOS host: a throwaway project with one PreToolUse Bash hook carrying if: Bash(git commit *) that appends its stdin to a log, then a nested claude -p running (1) a plain command, (2) a command quoting the phrase and (3) a multi-line heredoc mentioning it, and recording which of the three fired the hook. Uncontrolled evidence from this session (Claude Code 2.1.283, this repo's .claude/settings.json registers commit-prefix-guard with if: Bash(git commit *)): the hook fired and denied two commands that did not begin with the phrase and held it only inside a quoted function argument or inside a heredoc body. So if: did not keep the guard off those commands, either because it matches subcommands loosely or because it does not filter at all. That is why both guards now gate themselves and do not rely on if:.

Commit: `b643023` - task-281: gate commit guards on a real git commit and parse multi-line messages with a jq lexer

Review round 1 (task-reviewer: CHANGES REQUESTED, 1 blocking + 3 minor), all addressed. (1) Blocking: -S[<keyid>] and -u[<mode>] take only an attached value, so the short-option scan read through e.g. -unormal and found an m. Clusters now end at [mFCctSu], S and u never consume the next word, and there is a bats case. (2) prog now skips bare env/command/time/nice/nohup/exec wrappers, so env git... is gated again; bash -c strings and $( ) wrapping are still not seen, and those fail open. (3) A subject still holding $VAR, $( ) or a backtick, known only after expansion, now counts as no message and is allowed. Only the subject line is tested, so backticks in a body do not disable the check. (4) The bats file also passes 73/73 under jq 1.7.1 (the official jq-linux-arm64 release on PATH), as well as under the container's jq 1.6.

Commit: `04f69bf` - task-281: end short-option clusters at -S/-u, skip env/command/time wrappers, allow subjects that need expansion

Review round 2: task-reviewer APPROVED (0 blocking). Its one open minor point is the jq 1.7.1 run: the author ran it with the official jq-1.7.1 linux-arm64 binary first on PATH (73/73), and the reviewer, which had only jq 1.6, could not reproduce it. Final gates: LC_ALL=C bats tests/unit, 196 tests, only the R11 settings.local.json case failing (pre-existing; it depends on the gitignored local file); uv run pytest 913 passed, 3 skipped; ruff clean. Host follow-ups: /bin/bash -n on both guards, and the AC9 if: probe.

Commit: `8ad52c6` - task-281: bump plugin version to 0.14.8 (patch)
<!-- SECTION:NOTES:END -->
